use windows::{core::HSTRING, Data::Xml::Dom::XmlDocument, UI::Notifications::{NotificationSetting, ToastNotification, ToastNotificationManager}, Win32::System::WinRT::{RoInitialize, RO_INIT_MULTITHREADED}};

pub fn show(text: &str) -> Result<(), String> {
    if text.len() > 1000 { return Err("Notification text exceeds the supported size".into()); }
    unsafe { RoInitialize(RO_INIT_MULTITHREADED).map_err(|_| "Windows notification initialization failed")?; }
    let escaped = text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;").replace('\'', "&apos;");
    let xml = XmlDocument::new().map_err(|_| "Windows notification document unavailable")?;
    xml.LoadXml(&HSTRING::from(format!("<toast><visual><binding template=\"ToastGeneric\"><text>Trading Terminal</text><text>{escaped}</text></binding></visual><audio silent=\"true\"/></toast>"))).map_err(|_| "Windows notification document invalid")?;
    let toast=ToastNotification::CreateToastNotification(&xml).map_err(|_| "Cannot create Windows notification")?;
    let notifier=ToastNotificationManager::CreateToastNotifierWithId(&HSTRING::from("TradingTerminal.Research")).map_err(|_| "Windows notification identity unavailable")?;
    if notifier.Setting().map_err(|_| "Cannot read application notification setting")? != NotificationSetting::Enabled { return Err("Windows notifications are disabled for this application".into()); }
    notifier.Show(&toast).map_err(|_| "Windows notification delivery failed")?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // Opt-in only: emits a real notification and inspects only our own AUMID.
    // Windows retaining it is not proof of a visible banner or audible sound.
    #[test]
    #[ignore = "Requires an interactive Windows acceptance session and registered application identity"]
    fn windows_retains_application_notification() {
        let text = format!("Trading Terminal acceptance {}", std::process::id());
        show(&text).expect("native notification request");
        let history = ToastNotificationManager::History().expect("own notification history");
        for _ in 0..20 {
            let entries = history.GetHistoryWithId(&HSTRING::from("TradingTerminal.Research")).expect("own application notification history");
            for index in 0..entries.Size().unwrap() {
                let body = entries.GetAt(index).unwrap().Content().unwrap().InnerText().unwrap();
                if body.to_string().contains(&text) { return; }
            }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        panic!("Windows did not retain the application's test notification");
    }
}
