use std::{path::{Path, PathBuf}, process::{Command, Stdio}};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

pub fn default_python(root: &Path) -> PathBuf {
    #[cfg(windows)]
    let relative = ".venv/Scripts/python.exe";
    #[cfg(not(windows))]
    let relative = ".venv/bin/python";
    root.join(relative)
}

pub fn hide_console(command: &mut Command) {
    #[cfg(windows)]
    command.creation_flags(0x08000000);
    #[cfg(not(windows))]
    let _ = command;
}

pub fn exports_command(folder: &Path) -> Result<Command, String> {
    #[cfg(windows)]
    let program = "explorer.exe";
    #[cfg(target_os = "linux")]
    let program = "xdg-open";
    #[cfg(not(any(windows, target_os = "linux")))]
    return Err("Opening the exports folder is unavailable on this platform".into());

    #[cfg(any(windows, target_os = "linux"))]
    {
        if !folder.is_absolute() {
            return Err("Exports folder must be absolute".into());
        }
        let mut command = Command::new(program);
        // Pass the local path as one argument, never through a command shell.
        command.arg(folder).stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null());
        hide_console(&mut command);
        Ok(command)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsStr;

    #[test]
    fn project_python_uses_platform_venv_layout() {
        let root = Path::new("project with spaces");
        #[cfg(windows)]
        assert_eq!(default_python(root), root.join(".venv").join("Scripts").join("python.exe"));
        #[cfg(not(windows))]
        assert_eq!(default_python(root), root.join(".venv").join("bin").join("python"));
    }

    #[cfg(any(windows, target_os = "linux"))]
    #[test]
    fn exports_launcher_keeps_path_as_one_argument() {
        #[cfg(windows)]
        let folder = Path::new(r"C:\project with spaces\exports & reports");
        #[cfg(target_os = "linux")]
        let folder = Path::new("/project with spaces/exports & reports");
        let command = exports_command(folder).unwrap();
        #[cfg(windows)]
        assert_eq!(command.get_program(), OsStr::new("explorer.exe"));
        #[cfg(target_os = "linux")]
        assert_eq!(command.get_program(), OsStr::new("xdg-open"));
        assert_eq!(command.get_args().collect::<Vec<_>>(), vec![folder.as_os_str()]);
    }

    #[cfg(any(windows, target_os = "linux"))]
    #[test]
    fn exports_launcher_rejects_relative_paths() {
        assert_eq!(
            exports_command(Path::new("--relative-option")).unwrap_err(),
            "Exports folder must be absolute"
        );
    }
}
