import Foundation
import AppKit

@MainActor
class BackendManager: ObservableObject {
    @Published var isRunning = false
    @Published var port = 8420
    @Published var errorMessage: String?

    private var process: Process?
    private var healthCheckTask: Task<Void, Never>?

    var baseURL: String {
        "http://localhost:\(port)"
    }

    init() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(applicationWillTerminate),
            name: NSApplication.willTerminateNotification,
            object: nil
        )
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    @objc private func applicationWillTerminate() {
        stop()
    }

    func start() async {
        guard !isRunning else { return }

        errorMessage = nil

        // Get project directory from UserDefaults
        let projectDir = UserDefaults.standard.string(forKey: "projectDirectory") ?? NSHomeDirectory()

        // Try to find an available port, starting from 8420
        var testPort = 8420
        var foundPort = false

        for attempt in 0..<10 {
            testPort = 8420 + attempt

            // Check if backend is already running on this port
            if await healthCheck(port: testPort) {
                print("Backend already running on port \(testPort)")
                self.port = testPort
                self.isRunning = true
                return
            }

            // Check if port is available
            if isPortAvailable(testPort) {
                foundPort = true
                break
            }
        }

        guard foundPort else {
            errorMessage = "Could not find available port in range 8420-8430"
            return
        }

        self.port = testPort

        // Launch the backend process using the managed venv python
        let pythonPath = UserDefaults.standard.string(forKey: "pythonPath") ?? "/usr/bin/python3"

        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = ["-m", "stratagem", "--ui", "--port", "\(testPort)"]
        process.currentDirectoryURL = URL(fileURLWithPath: projectDir)

        // Capture stderr for error reporting
        let errorPipe = Pipe()
        process.standardError = errorPipe

        do {
            try process.run()
            self.process = process

            // Start monitoring stderr in background
            Task.detached { [weak self] in
                let handle = errorPipe.fileHandleForReading
                while let data = try? handle.availableData, !data.isEmpty {
                    if let errorStr = String(data: data, encoding: .utf8) {
                        await MainActor.run {
                            print("Backend stderr: \(errorStr)")
                            if let self = self, !self.isRunning {
                                self.errorMessage = errorStr.trimmingCharacters(in: .whitespacesAndNewlines)
                            }
                        }
                    }
                }
            }

            // Wait for backend to be ready
            for _ in 0..<30 {
                try? await Task.sleep(for: .milliseconds(500))
                if await healthCheck(port: testPort) {
                    self.isRunning = true
                    print("Backend started successfully on port \(testPort)")
                    return
                }
            }

            // Timeout
            process.terminate()
            self.process = nil
            errorMessage = "Backend failed to start within 15 seconds"

        } catch {
            errorMessage = "Failed to launch backend: \(error.localizedDescription)"
        }
    }

    func stop() {
        guard let process = process else { return }

        if process.isRunning {
            process.terminate()
            process.waitUntilExit()
        }

        self.process = nil
        self.isRunning = false
    }

    private func healthCheck(port: Int) async -> Bool {
        guard let url = URL(string: "http://localhost:\(port)/api/health") else {
            return false
        }

        var request = URLRequest(url: url)
        request.timeoutInterval = 2

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse {
                return httpResponse.statusCode == 200
            }
            return false
        } catch {
            return false
        }
    }

    private func isPortAvailable(_ port: Int) -> Bool {
        let socketFD = socket(AF_INET, SOCK_STREAM, 0)
        guard socketFD != -1 else { return false }

        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = in_port_t(port).bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")

        let bindResult = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                bind(socketFD, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }

        close(socketFD)

        return bindResult == 0
    }
}
