import Foundation

// MARK: - Types

enum SetupPhase: Equatable {
    case welcome
    case checking
    case needsUv
    case installingUv
    case installingStratagem
    case chooseDirectory
    case ready
    case failed(String)
}

enum CheckStatus: Equatable {
    case pending
    case checking
    case installed
    case missing
    case installing
    case failed(String)
}

// MARK: - SetupManager

@MainActor
class SetupManager: ObservableObject {
    @Published var phase: SetupPhase = .welcome
    @Published var uvStatus: CheckStatus = .pending
    @Published var stratagemStatus: CheckStatus = .pending
    @Published var statusText: String = ""
    @Published var projectDirectory: String = ""
    @Published var developmentMode = false
    @Published var devModePath: String = ""
    @Published var errorMessage: String?

    private var uvPath: String = ""
    private var currentProcess: Process?

    /// Step 1 is complete when both uv and stratagem are installed
    var installComplete: Bool {
        uvStatus == .installed && stratagemStatus == .installed
    }

    /// Everything is done — ready to launch
    var allComplete: Bool {
        installComplete && !projectDirectory.isEmpty
            && (!developmentMode || !devModePath.isEmpty)
    }

    /// Needs manual uv install action
    var needsUvInstall: Bool {
        phase == .needsUv
    }

    var appSupportDir: String {
        let paths = NSSearchPathForDirectoriesInDomains(
            .applicationSupportDirectory, .userDomainMask, true
        )
        return (paths.first! as NSString).appendingPathComponent("Stratagem")
    }

    var venvPath: String {
        (appSupportDir as NSString).appendingPathComponent("venv")
    }

    var venvPython: String {
        (venvPath as NSString).appendingPathComponent("bin/python")
    }

    init() {
        loadConfiguration()
    }

    func loadConfiguration() {
        if let savedDir = UserDefaults.standard.string(forKey: "projectDirectory") {
            projectDirectory = savedDir
        } else {
            let docs = NSSearchPathForDirectoriesInDomains(
                .documentDirectory, .userDomainMask, true
            ).first!
            projectDirectory = (docs as NSString).appendingPathComponent("Stratagem")
        }

        developmentMode = UserDefaults.standard.bool(forKey: "developmentMode")

        if let savedDevPath = UserDefaults.standard.string(forKey: "devModePath") {
            devModePath = savedDevPath
        }
    }

    // MARK: - Setup Flow

    func startSetup() async {
        phase = .checking
        errorMessage = nil
        uvStatus = .checking
        statusText = "Looking for Python tools..."

        if let path = await findUv() {
            uvPath = path
            uvStatus = .installed
            await checkAndInstallStratagem()
        } else {
            uvStatus = .missing
            phase = .needsUv
            statusText = ""
        }
    }

    func installUv() async {
        phase = .installingUv
        errorMessage = nil
        uvStatus = .installing
        statusText = "Downloading package manager..."

        let _ = await runCommandStreaming(
            "/bin/sh",
            arguments: ["-c", "curl -LsSf https://astral.sh/uv/install.sh | sh 2>&1"]
        )

        // uv installs to ~/.local/bin/uv
        let homeDir = NSHomeDirectory()
        let localUvPath = (homeDir as NSString).appendingPathComponent(".local/bin/uv")

        if FileManager.default.fileExists(atPath: localUvPath) {
            uvPath = localUvPath
            uvStatus = .installed
            await checkAndInstallStratagem()
        } else if let path = await findUv() {
            uvPath = path
            uvStatus = .installed
            await checkAndInstallStratagem()
        } else {
            uvStatus = .failed("Not found after install")
            errorMessage = "Package manager was downloaded but couldn't be located. Try restarting the app."
            phase = .failed("uv install failed")
        }
    }

    private func checkAndInstallStratagem() async {
        stratagemStatus = .checking
        statusText = "Checking research engine..."

        try? FileManager.default.createDirectory(
            atPath: appSupportDir,
            withIntermediateDirectories: true
        )

        // Check if venv already has a working stratagem
        if FileManager.default.fileExists(atPath: venvPython) {
            if await verifyStratagem() {
                stratagemStatus = .installed
                statusText = ""
                phase = .chooseDirectory
                return
            }
        }

        await installStratagem()
    }

    func installStratagem() async {
        phase = .installingStratagem
        errorMessage = nil
        stratagemStatus = .installing
        statusText = "Creating Python environment..."

        // Always ensure venv exists before installing
        if !FileManager.default.fileExists(atPath: venvPython) {
            let _ = await runCommandStreaming(
                uvPath,
                arguments: ["venv", venvPath, "--python", "3.12"]
            )

            guard FileManager.default.fileExists(atPath: venvPython) else {
                stratagemStatus = .failed("Environment creation failed")
                errorMessage = "Could not create Python environment. Check your internet connection — uv needs to download Python 3.12."
                phase = .failed("venv creation failed")
                return
            }
        } else {
            // Venv exists but might be broken — verify python binary works
            let testResult = await runCommand(venvPython, arguments: ["--version"])
            if testResult.isEmpty || testResult.contains("error") {
                // Recreate broken venv
                try? FileManager.default.removeItem(atPath: venvPath)
                let _ = await runCommandStreaming(
                    uvPath,
                    arguments: ["venv", venvPath, "--python", "3.12"]
                )
                guard FileManager.default.fileExists(atPath: venvPython) else {
                    stratagemStatus = .failed("Environment recreation failed")
                    errorMessage = "Python environment was broken and could not be recreated."
                    phase = .failed("venv recreation failed")
                    return
                }
            }
        }

        statusText = "Installing packages..."

        // Build install args — auto-detect source tree if not in explicit dev mode
        var installArgs = ["pip", "install"]
        if developmentMode && !devModePath.isEmpty {
            // Validate the source path exists and has pyproject.toml
            let pyproject = (devModePath as NSString).appendingPathComponent("pyproject.toml")
            guard FileManager.default.fileExists(atPath: pyproject) else {
                stratagemStatus = .failed("Source folder not valid")
                errorMessage = "No pyproject.toml found at \"\(devModePath)\". Make sure the path points to the stratagem source code folder."
                phase = .failed("invalid dev path")
                return
            }
            installArgs += ["-e", devModePath]
        } else if let sourcePath = detectSourceTree() {
            // Found local source checkout — install from it
            installArgs += ["-e", sourcePath]
            devModePath = sourcePath
            developmentMode = true
            statusText = "Installing from local source..."
        } else {
            installArgs += ["stratagem"]
        }
        installArgs += ["--python", venvPython]

        let _ = await runCommandStreaming(uvPath, arguments: installArgs)

        // Verify with a deep import
        statusText = "Verifying..."
        if await verifyStratagem() {
            stratagemStatus = .installed
            statusText = ""
            errorMessage = nil
            phase = .chooseDirectory
        } else {
            stratagemStatus = .failed("Import failed after install")
            if developmentMode {
                errorMessage = "Installation from local source failed. Check that the source path is correct and contains valid Python code."
            } else {
                errorMessage = "Could not install the research engine. If you have the source code, expand \"For contributors\" and enable local source install."
            }
            phase = .failed("stratagem install failed")
        }
    }

    /// Deep import check — avoids false positives from namespace packages
    private func verifyStratagem() async -> Bool {
        let result = await runCommand(
            venvPython,
            arguments: ["-c", "from stratagem.server import create_stratagem_server; print('OK')"]
        )
        return result.contains("OK")
    }

    /// Auto-detect stratagem source tree by looking for pyproject.toml
    private func detectSourceTree() -> String? {
        let home = NSHomeDirectory()
        var candidates = [
            (home as NSString).appendingPathComponent("Desktop/git-folder/stratagem"),
        ]

        // Also check near the project directory
        if !projectDirectory.isEmpty {
            let parent = (projectDirectory as NSString).deletingLastPathComponent
            candidates.append(parent)
            candidates.append(
                (parent as NSString).appendingPathComponent("stratagem")
            )
        }

        for path in candidates {
            let pyproject = (path as NSString).appendingPathComponent("pyproject.toml")
            if FileManager.default.fileExists(atPath: pyproject) {
                if let content = try? String(contentsOfFile: pyproject, encoding: .utf8),
                    content.contains("name = \"stratagem\"")
                {
                    return path
                }
            }
        }

        return nil
    }

    func completeSetup() {
        try? FileManager.default.createDirectory(
            atPath: projectDirectory,
            withIntermediateDirectories: true
        )
        saveConfiguration()
        phase = .ready
    }

    func saveConfiguration() {
        try? FileManager.default.createDirectory(
            atPath: projectDirectory,
            withIntermediateDirectories: true
        )
        UserDefaults.standard.set(venvPython, forKey: "pythonPath")
        UserDefaults.standard.set(projectDirectory, forKey: "projectDirectory")
        UserDefaults.standard.set(developmentMode, forKey: "developmentMode")
        UserDefaults.standard.set(devModePath, forKey: "devModePath")
        UserDefaults.standard.set(uvPath, forKey: "uvPath")
    }

    func retry() async {
        uvStatus = .pending
        stratagemStatus = .pending
        statusText = ""
        errorMessage = nil
        await startSetup()
    }

    // MARK: - Find uv

    private func findUv() async -> String? {
        let homeDir = NSHomeDirectory()
        let candidates = [
            (homeDir as NSString).appendingPathComponent(".local/bin/uv"),
            "/opt/homebrew/bin/uv",
            "/usr/local/bin/uv",
            (homeDir as NSString).appendingPathComponent(".cargo/bin/uv"),
        ]

        for path in candidates {
            if FileManager.default.fileExists(atPath: path) {
                return path
            }
        }

        // Fallback: which
        let result = await runCommand("/usr/bin/env", arguments: ["which", "uv"])
        let trimmed = result.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty && !trimmed.contains("not found")
            && FileManager.default.fileExists(atPath: trimmed)
        {
            return trimmed
        }

        return nil
    }

    // MARK: - Command Execution

    private func runCommand(
        _ command: String,
        arguments: [String]
    ) async -> String {
        await withCheckedContinuation { continuation in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: command)
            process.arguments = arguments

            let pipe = Pipe()
            process.standardOutput = pipe
            process.standardError = pipe

            do {
                try process.run()

                // Resume asynchronously instead of blocking with waitUntilExit()
                process.terminationHandler = { _ in
                    let data = pipe.fileHandleForReading.readDataToEndOfFile()
                    let output = String(data: data, encoding: .utf8) ?? ""
                    continuation.resume(returning: output)
                }
            } catch {
                continuation.resume(returning: "")
            }
        }
    }

    private func runCommandStreaming(
        _ command: String,
        arguments: [String]
    ) async -> String {
        await withCheckedContinuation { continuation in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: command)
            process.arguments = arguments

            let stdoutPipe = Pipe()
            let stderrPipe = Pipe()
            process.standardOutput = stdoutPipe
            process.standardError = stderrPipe

            // Serial queue protects allOutput from concurrent writes
            let outputQueue = DispatchQueue(label: "stratagem.command-output")
            var allOutput = ""

            // Stream stderr for progress updates
            stderrPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
                let data = handle.availableData
                guard !data.isEmpty,
                    let text = String(data: data, encoding: .utf8)
                else { return }
                outputQueue.sync { allOutput += text }

                Task { @MainActor [weak self] in
                    let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
                    if let lastLine = trimmed.components(separatedBy: .newlines).last,
                        !lastLine.isEmpty
                    {
                        self?.statusText = Self.humanizeProgress(lastLine)
                    }
                }
            }

            // Collect stdout
            stdoutPipe.fileHandleForReading.readabilityHandler = { handle in
                let data = handle.availableData
                guard !data.isEmpty,
                    let text = String(data: data, encoding: .utf8)
                else { return }
                outputQueue.sync { allOutput += text }
            }

            self.currentProcess = process

            do {
                try process.run()

                // Resume asynchronously instead of blocking with waitUntilExit()
                process.terminationHandler = { [weak self] _ in
                    stderrPipe.fileHandleForReading.readabilityHandler = nil
                    stdoutPipe.fileHandleForReading.readabilityHandler = nil

                    let result = outputQueue.sync { allOutput }

                    Task { @MainActor in
                        self?.currentProcess = nil
                    }
                    continuation.resume(returning: result)
                }
            } catch {
                self.currentProcess = nil
                continuation.resume(returning: "error: \(error.localizedDescription)")
            }
        }
    }

    private static func humanizeProgress(_ line: String) -> String {
        let lower = line.lowercased()

        if lower.contains("resolved") {
            return "Resolving dependencies..."
        }
        if lower.contains("prepared") || lower.contains("downloading") {
            let parts = line.components(separatedBy: " ")
            if parts.count >= 2 {
                let raw = parts.last ?? parts[1]
                let pkg = raw.components(separatedBy: "==").first?
                    .components(separatedBy: "-").first ?? raw
                return "Downloading \(pkg)..."
            }
            return "Downloading packages..."
        }
        if lower.contains("installing") || lower.contains("installed") {
            return "Installing packages..."
        }
        if lower.contains("building") {
            return "Building components..."
        }
        if lower.contains("audited") || lower.contains("successfully") {
            return "Finishing up..."
        }
        if lower.contains("created virtual") {
            return "Python environment created"
        }
        if lower.contains("using python") || lower.contains("using cpython") {
            return "Setting up Python..."
        }

        if line.count > 50 {
            return String(line.prefix(47)) + "..."
        }
        return line
    }
}
