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

    private var uvPath: String = ""
    private var currentProcess: Process?

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
        uvStatus = .checking
        statusText = "Looking for package manager..."

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
        uvStatus = .installing
        statusText = "Downloading uv..."

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
            phase = .failed(
                "uv was downloaded but couldn't be located. Try restarting the app."
            )
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
            let importCheck = await runCommand(
                venvPython,
                arguments: ["-c", "import stratagem; print('OK')"]
            )

            if importCheck.contains("OK") {
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
        stratagemStatus = .installing
        statusText = "Creating Python environment..."

        // Create venv if needed
        if !FileManager.default.fileExists(atPath: venvPython) {
            let _ = await runCommandStreaming(
                uvPath,
                arguments: ["venv", venvPath, "--python", "3.12"]
            )

            guard FileManager.default.fileExists(atPath: venvPython) else {
                stratagemStatus = .failed("Environment creation failed")
                phase = .failed(
                    "Could not create Python environment. Ensure you have internet access so uv can download Python 3.12."
                )
                return
            }
        }

        statusText = "Installing packages..."

        // Build install args
        var installArgs = ["pip", "install"]
        if developmentMode && !devModePath.isEmpty {
            installArgs += ["-e", devModePath]
        } else {
            installArgs += ["stratagem"]
        }
        installArgs += ["--python", venvPython]

        let _ = await runCommandStreaming(uvPath, arguments: installArgs)

        // Verify import works
        statusText = "Verifying..."
        let verifyResult = await runCommand(
            venvPython,
            arguments: ["-c", "import stratagem; print('OK')"]
        )

        if verifyResult.contains("OK") {
            stratagemStatus = .installed
            statusText = ""
            phase = .chooseDirectory
        } else {
            stratagemStatus = .failed("Import failed after install")
            phase = .failed(
                "Packages installed but stratagem couldn't be loaded. Check your internet connection and try again."
            )
        }
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
                process.waitUntilExit()

                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8) ?? ""
                continuation.resume(returning: output)
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

            var allOutput = ""

            // Stream stderr for progress updates
            stderrPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
                let data = handle.availableData
                guard !data.isEmpty,
                    let text = String(data: data, encoding: .utf8)
                else { return }
                allOutput += text

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
                allOutput += text
            }

            self.currentProcess = process

            do {
                try process.run()
                process.waitUntilExit()

                stderrPipe.fileHandleForReading.readabilityHandler = nil
                stdoutPipe.fileHandleForReading.readabilityHandler = nil

                self.currentProcess = nil
                continuation.resume(returning: allOutput)
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
            // uv outputs: "Prepared lxml==5.3.1" or "Downloading httpx-0.28.0"
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
