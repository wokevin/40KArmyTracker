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
        private bool _isSaved;

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

        private string _dataSourceFolder;
        public string DataSourceFolder
        {
            get => _dataSourceFolder;
            set
            {
                if (SetProperty(ref _dataSourceFolder, value))
                    IsSaved = false;
            }
        }

        private string _rostersSaveFolder;
        public string RostersSaveFolder
        {
            get => _rostersSaveFolder;
            set
            {
                if (SetProperty(ref _rostersSaveFolder, value))
                    IsSaved = false;
            }
        }

        private int _defaultPointsLimit;
        public int DefaultPointsLimit
        {
            get => _defaultPointsLimit;
            set
            {
                if (SetProperty(ref _defaultPointsLimit, value))
                    IsSaved = false;
            }
        }

        public bool IsSaved
        {
            get => _isSaved;
            set => SetProperty(ref _isSaved, value);
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
            IsSaved = true;
        }
    }
}