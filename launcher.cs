using System;
using System.Diagnostics;
using System.IO;

namespace FluidCursorLauncher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            string appDir = AppDomain.CurrentDomain.BaseDirectory;
            string mainPy = Path.Combine(appDir, "main.py");
            
            // Priority 1: User's Python installation
            string pythonw = @"C:\Users\osama\AppData\Local\Programs\Python\Python312\pythonw.exe";
            if (!File.Exists(pythonw))
            {
                pythonw = FindInPath("pythonw.exe");
            }
            if (string.IsNullOrEmpty(pythonw) || !File.Exists(pythonw))
            {
                pythonw = @"C:\Users\osama\AppData\Local\Programs\Python\Python312\python.exe";
                if (!File.Exists(pythonw))
                {
                    pythonw = FindInPath("python.exe");
                }
            }

            string arguments = "\"" + mainPy + "\"";
            if (args != null && args.Length > 0)
            {
                arguments += " " + string.Join(" ", args);
            }

            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = !string.IsNullOrEmpty(pythonw) ? pythonw : "pythonw.exe",
                Arguments = arguments,
                WorkingDirectory = appDir,
                UseShellExecute = true,
                Verb = "runas" // Elevate to High Integrity to capture mouse events over Task Manager
            };

            try
            {
                Process.Start(psi);
            }
            catch (System.ComponentModel.Win32Exception)
            {
                // If user declines UAC prompt, launch with standard user privileges
                psi.Verb = "";
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                try
                {
                    Process.Start(psi);
                }
                catch (Exception ex2)
                {
                    System.Windows.Forms.MessageBox.Show(
                        "Failed to launch FluidCursor: " + ex2.Message,
                        "FluidCursor Launcher Error",
                        System.Windows.Forms.MessageBoxButtons.OK,
                        System.Windows.Forms.MessageBoxIcon.Error
                    );
                }
            }
            catch (Exception ex)
            {
                System.Windows.Forms.MessageBox.Show(
                    "Failed to launch FluidCursor: " + ex.Message,
                    "FluidCursor Launcher Error",
                    System.Windows.Forms.MessageBoxButtons.OK,
                    System.Windows.Forms.MessageBoxIcon.Error
                );
            }
        }

        static string FindInPath(string filename)
        {
            string pathEnv = Environment.GetEnvironmentVariable("PATH");
            if (string.IsNullOrEmpty(pathEnv)) return null;

            string[] paths = pathEnv.Split(';');
            foreach (string p in paths)
            {
                try
                {
                    string full = Path.Combine(p.Trim(), filename);
                    if (File.Exists(full)) return full;
                }
                catch { }
            }
            return null;
        }
    }
}
