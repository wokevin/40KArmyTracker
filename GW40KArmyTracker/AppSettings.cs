using System;
using System.IO;
using System.Text.Json;
using Windows.Storage;

namespace GW40KArmyTracker.Services
{
    public class AppSettings
    {
        private const string SettingsFileName = "settings.json";

        public string DataSourceFolder { get; set; } = string.Empty;
        public string RostersSaveFolder { get; set; } = string.Empty;
        public int DefaultPointsLimit { get; set; } = 2000;

        private static string SettingsFilePath =>
            Path.Combine(ApplicationData.Current.LocalFolder.Path, SettingsFileName);

        public static AppSettings Load()
        {
            try
            {
                if (File.Exists(SettingsFilePath))
                {
                    string json = File.ReadAllText(SettingsFilePath);
                    AppSettings? settings = JsonSerializer.Deserialize<AppSettings>(json);
                    return settings ?? new AppSettings();
                }
            }
            catch
            {
                // Fall through to default
            }
            return new AppSettings();
        }

        public void Save()
        {
            string json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(SettingsFilePath, json);
        }
    }
}