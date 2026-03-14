import Foundation

@MainActor
class SetupManager: ObservableObject {
    @Published var pythonPath: String = ""
    @Published var projectDirectory: String = NSHomeDirectory()
    @Published var uvAvailable = false
    @Published var isChecking = false
    @Published var errorMessage: String?
    @Published var developmentMode = false
    @Published var devModePath: String = ""

    init() {
        loadConfiguration()
    }

    func loadConfiguration() {
        if let savedPythonPath = UserDefaults.standard.string(forKey: "pythonPath") {
            pythonPath = savedPythonPath
        }

        if let savedProjectDir = UserDefaults.standard.string(forKey: "projectDirectory") {
            projectDirectory = savedProjectDir
        }

        if let savedDevMode = UserDefaults.standard.object(forKey: "developmentMode") as? Bool {
            developmentMode = savedDevMode
        }

        if let savedDevPath = UserDefaults.standard.string(forKey: "devModePath") {
            devModePath = savedDevPath
        } else {
            // Default to parent directory of projectDirectory
            devModePath = (projectDirectory as NSString).deletingLastPathComponent + "/stratagem"
        }
    }

    func detectEnvironment() async {
        isChecking = true
        errorMessage = nil

        // Check for uv in PATH
        let uvPath = await runCommand("/usr/bin/env", arguments: ["which", "uv"])
        uvAvailable = !uvPath.isEmpty && !uvPath.contains("not found")

        if uvAvailable {
            // Use uv to find python
            let pythonResult = await runCommand("/usr/bin/env", arguments: ["uv", "run", "python", "--version"])
            if pythonResult.contains("Python") {
                pythonPath = "uv run python"
            } else {
                errorMessage = "uv found but Python not available"
            }
        } else {
            // Fallback to system python3
            let python3Path = await runCommand("/usr/bin/env", arguments: ["which", "python3"])
            if !python3Path.isEmpty {
                pythonPath = python3Path.trimmingCharacters(in: .whitespacesAndNewlines)
            } else {
                errorMessage = "Neither uv nor python3 found in PATH"
            }
        }

        isChecking = false
    }

    func validateSetup() async -> Bool {
        isChecking = true
        errorMessage = nil

        var importCheck: String

        if developmentMode && !devModePath.isEmpty {
            // Install in development mode first
            let installResult = await runCommand(
                "/usr/bin/env",
                arguments: ["uv", "pip", "install", "-e", devModePath],
                workingDirectory: projectDirectory
            )

            if installResult.contains("error") || installResult.contains("Error") {
                errorMessage = "Failed to install stratagem in development mode: \(installResult)"
                isChecking = false
                return false
            }
        }

        // Validate that stratagem can be imported
        importCheck = await runCommand(
            "/usr/bin/env",
            arguments: ["uv", "run", "python", "-c", "import stratagem; print('OK')"],
            workingDirectory: projectDirectory
        )

        let isValid = importCheck.contains("OK")

        if !isValid {
            errorMessage = "Could not import stratagem module. Ensure it's installed in the project directory."
        }

        isChecking = false
        return isValid
    }

    func saveConfiguration() {
        UserDefaults.standard.set(pythonPath, forKey: "pythonPath")
        UserDefaults.standard.set(projectDirectory, forKey: "projectDirectory")
        UserDefaults.standard.set(developmentMode, forKey: "developmentMode")
        UserDefaults.standard.set(devModePath, forKey: "devModePath")
    }

    private func runCommand(
        _ command: String,
        arguments: [String],
        workingDirectory: String? = nil
    ) async -> String {
        await withCheckedContinuation { continuation in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: command)
            process.arguments = arguments

            if let workingDir = workingDirectory {
                process.currentDirectoryURL = URL(fileURLWithPath: workingDir)
            }

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
}
