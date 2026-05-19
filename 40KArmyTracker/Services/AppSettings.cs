using System;
using System.IO;
using System.Text.Json;

namespace GW40KArmyTracker.Services
{
    public class AppSettings
    {
        private const string SettingsFileName = "settings.json";
        private static AppSettings? _instance;
        private static readonly object _lock = new object();

        public string DefaultDataSourceFolder { get; set; } = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data");
        public string RostersSaveFolder { get; set; } = string.Empty;
        public int DefaultPointsLimit { get; set; } = 2000;

        private static string AppDataPath => Path.Combine( Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "GW40KArmyTracker" );
        private static string SettingsFilePath => Path.Combine(AppDataPath, SettingsFileName);
        public static string DefaultRostersFolder => Path.Combine(AppDataPath, "Rosters");

        public static AppSettings Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_lock)
                    {
                        if (_instance == null)
                        {
                            _instance = Load();
                        }
                    }
                }
                return _instance;
            }
        }

        private static AppSettings Load()
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

        public static void Reload()
        {
            lock (_lock)
            {
                _instance = Load();
            }
        }
    }
}