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

        private static string AppDataPath => ApplicationData.Current.LocalFolder.Path;
        private static string SettingsFilePath => Path.Combine(AppDataPath, SettingsFileName);
        public static string DefaultRostersFolder => Path.Combine(AppDataPath, "Rosters");

        public static AppSettings Load()
        {
            try
            {
                if (File.Exists(SettingsFilePath))
                {
                    string json = File.ReadAllText(SettingsFilePath);
                    AppSettings? settings = JsonSerializer.Deserialize<AppSettings>(json);
                    if (settings != null)
                    {
                        // Set default rosters folder if empty
                        if (string.IsNullOrEmpty(settings.RostersSaveFolder))
                        {
                            settings.RostersSaveFolder = DefaultRostersFolder;
                        }
                        return settings;
                    }
                }
            }
            catch
            {
            }

            // Return new settings with default rosters folder
            AppSettings defaultSettings = new()
            {
                RostersSaveFolder = DefaultRostersFolder
            };
            return defaultSettings;
        }

        public void Save()
        {
            // Ensure rosters folder exists
            if (!string.IsNullOrEmpty(RostersSaveFolder) && !Directory.Exists(RostersSaveFolder))
            {
                Directory.CreateDirectory(RostersSaveFolder);
            }

            string json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(SettingsFilePath, json);
        }
    }
}