using System;
using System.Windows.Input;
using Windows.Storage.Pickers;
using GW40KArmyTracker.Services;
using WinRT.Interop;

namespace GW40KArmyTracker.ViewModels
{
    public sealed class SettingsViewModel : ObservableObject
    {
        private readonly AppSettings _settings;

        public SettingsViewModel()
        {
            _settings = AppSettings.Load();
            _dataSourceFolder = _settings.DataSourceFolder;
            _rostersSaveFolder = _settings.RostersSaveFolder;
            _defaultPointsLimit = _settings.DefaultPointsLimit;

            BrowseDataSourceCommand = new RelayCommand(BrowseDataSource);
            BrowseRostersFolderCommand = new RelayCommand(BrowseRostersFolder);
            SaveCommand = new RelayCommand(Save);
        }

        private string _dataSourceFolder = string.Empty;
        public string DataSourceFolder
        {
            get => _dataSourceFolder;
            set => SetProperty(ref _dataSourceFolder, value);
        }

        private string _rostersSaveFolder = string.Empty;
        public string RostersSaveFolder
        {
            get => _rostersSaveFolder;
            set => SetProperty(ref _rostersSaveFolder, value);
        }

        private int _defaultPointsLimit;
        public int DefaultPointsLimit
        {
            get => _defaultPointsLimit;
            set => SetProperty(ref _defaultPointsLimit, value);
        }

        public ICommand BrowseDataSourceCommand { get; }
        public ICommand BrowseRostersFolderCommand { get; }
        public ICommand SaveCommand { get; }

        private async void BrowseDataSource()
        {
            FolderPicker picker = new();
            picker.SuggestedStartLocation = PickerLocationId.DocumentsLibrary;
            picker.FileTypeFilter.Add("*");

            IntPtr hwnd = WindowNative.GetWindowHandle(App.MainWindow);
            InitializeWithWindow.Initialize(picker, hwnd);

            Windows.Storage.StorageFolder? folder = await picker.PickSingleFolderAsync();
            if (folder != null)
            {
                DataSourceFolder = folder.Path;
            }
        }

        private async void BrowseRostersFolder()
        {
            FolderPicker picker = new();
            picker.SuggestedStartLocation = PickerLocationId.DocumentsLibrary;
            picker.FileTypeFilter.Add("*");

            IntPtr hwnd = WindowNative.GetWindowHandle(App.MainWindow);
            InitializeWithWindow.Initialize(picker, hwnd);

            Windows.Storage.StorageFolder? folder = await picker.PickSingleFolderAsync();
            if (folder != null)
            {
                RostersSaveFolder = folder.Path;
            }
        }

        private void Save()
        {
            _settings.DataSourceFolder = DataSourceFolder;
            _settings.RostersSaveFolder = RostersSaveFolder;
            _settings.DefaultPointsLimit = DefaultPointsLimit;
            _settings.Save();
        }
    }
}