using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Navigation;
using GW40KArmyTracker.ViewModels;
using GW40KArmyTracker.Models;
using GW40KArmyTracker.Services;
using System.Collections.ObjectModel;
using System.Linq;
using System;
using Microsoft.UI.Xaml;
using System.IO;
using Microsoft.UI.Xaml.Input;
using Microsoft.UI.Text;
using System.Collections.Generic;
using GW40KArmyTracker.Dialogs;
using GW40KArmyTracker.Pages;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class RosterEditorPage : Page
    {
        private ArmyRosterViewModel _roster;
        private Catalog? _armyCatalog;
        private readonly ObservableCollection<ArmyRosterViewModel> savedRosters = new ObservableCollection<ArmyRosterViewModel>();

        // Bucket collections - one for each category
        public ObservableCollection<Unit> Characters { get; } = new ObservableCollection<Unit>();
        public ObservableCollection<Unit> Vehicles { get; } = new ObservableCollection<Unit>();
        public ObservableCollection<Unit> Squads { get; } = new ObservableCollection<Unit>();
        public ObservableCollection<Unit> Infantry { get; } = new ObservableCollection<Unit>();
        public ObservableCollection<Unit> Other { get; } = new ObservableCollection<Unit>();
        
        public string RosterName => _roster?.RosterName ?? string.Empty;
        public string ArmyName => _roster?.ArmyName ?? string.Empty;
        public int TotalPoints => _roster?.TotalPoints ?? 0;
        public int PointLimit => _roster?.PointLimit ?? 0;
        public int RemainingPoints => _roster?.RemainingPoints ?? 0;

        internal ObservableCollection<ArmyRosterViewModel> SavedRosters
        {
            get
            {
                return savedRosters;
            }
        }

        public bool IsRosterLoaded => _roster != null && !string.IsNullOrEmpty(_roster.RosterName);
        public Visibility RosterSelectionVisibility => IsRosterLoaded ? Visibility.Collapsed : Visibility.Visible;
        public Visibility RosterEditorVisibility => IsRosterLoaded ? Visibility.Visible : Visibility.Collapsed;

        public RosterEditorPage()
        {
            this.InitializeComponent();
            _roster = new ArmyRosterViewModel();
        }

        protected override void OnNavigatedTo(NavigationEventArgs e)
        {
            base.OnNavigatedTo(e);

            if (e.Parameter is ArmyRosterViewModel roster)
            {
                _roster = roster;
                LoadArmyCatalog();
            }
            else
            {
                LoadSavedRosters();
            }
            
            Bindings.Update();
        }

        private void LoadArmyCatalog()
        {
            if (_roster == null)
                return;

            AppSettings settings = AppSettings.Instance;
            string dataFolder = settings.DefaultDataSourceFolder;

            if (string.IsNullOrEmpty(dataFolder) || !Directory.Exists(dataFolder))
            {
                // Handle error
                return;
            }

            // Load all catalogs
            List<Catalog> catalogs = BattleScribeParser.Instance.LoadCatalogsFromFolder(dataFolder);

            // Find the matching catalog
            _armyCatalog = catalogs.FirstOrDefault(c =>
                c.Name.Equals(_roster.ArmyName, StringComparison.OrdinalIgnoreCase));

            if (_armyCatalog == null)
                return;

            LoadAvailableUnits();
        }

        private void LoadAvailableUnits()
        {
            // Clear all bucket collections
            Characters.Clear();
            Vehicles.Clear();
            Squads.Clear();
            Infantry.Clear();
            Other.Clear();

            if (_armyCatalog == null)
            {
                System.Diagnostics.Debug.WriteLine("_armyCatalog is null");
                return;
            }

            System.Diagnostics.Debug.WriteLine($"Found {_armyCatalog.Units.Count} units in catalog");

            // Populate bucket collections based on unit keywords
            foreach (Unit unit in _armyCatalog.Units)
            {
                System.Diagnostics.Debug.WriteLine($"Unit: {unit.Name}, Keywords: {string.Join(", ", unit.Keywords)}");
                
                string bucketName = GetBucketNameForUnit(unit);
                System.Diagnostics.Debug.WriteLine($"  -> Bucket: {bucketName}");
                
                switch (bucketName)
                {
                    case "Characters":
                        Characters.Add(unit);
                        break;
                    case "Vehicles":
                        Vehicles.Add(unit);
                        break;
                    case "Squads":
                        Squads.Add(unit);
                        break;
                    case "Infantry":
                        Infantry.Add(unit);
                        break;
                    case "Other":
                        Other.Add(unit);
                        break;
                }
            }
            
            System.Diagnostics.Debug.WriteLine($"Populated buckets - Characters: {Characters.Count}, Vehicles: {Vehicles.Count}, Squads: {Squads.Count}, Infantry: {Infantry.Count}, Other: {Other.Count}");
        }

        private string GetBucketNameForUnit(Unit unit)
        {
            if (unit.Keywords.Any(k => k.Contains("Character", StringComparison.OrdinalIgnoreCase)))
                return "Characters";
            if (unit.Keywords.Any(k => k.Contains("Vehicle", StringComparison.OrdinalIgnoreCase)))
                return "Vehicles";
            if (unit.Keywords.Any(k => k.Contains("Squad", StringComparison.OrdinalIgnoreCase)))
                return "Squads";
            if (unit.Keywords.Any(k => k.Contains("Infantry", StringComparison.OrdinalIgnoreCase)))
                return "Infantry";
            return "Other";
        }

        private void AddUnitButton_Click(object sender, Microsoft.UI.Xaml.RoutedEventArgs e)
        {
            if (sender is Button button && button.DataContext is Unit unit)
            {
                _roster.AddSelection(unit.Id, 1, unit.PointsCost);
                Bindings.Update();
            }
        }

        private async void LoadRoster_Click(object sender, RoutedEventArgs e)
        {
            Windows.Storage.Pickers.FileOpenPicker picker = new Windows.Storage.Pickers.FileOpenPicker();
            picker.FileTypeFilter.Add(".json");
            
            // Get the window handle for WinUI 3
            IntPtr hwnd = WinRT.Interop.WindowNative.GetWindowHandle(App.MainWindow);
            WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd);
            
            Windows.Storage.StorageFile? file = await picker.PickSingleFileAsync();
            
            if (file != null)
            {
                ArmyRosterViewModel? roster = ArmyRosterViewModel.LoadFromFile(file.Path);
                
                if (roster != null)
                {
                    Frame.Navigate(typeof(RosterEditorPage), roster);
                }
            }
        }

        private void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            if (_roster == null) return;
            
            AppSettings settings = AppSettings.Instance;
            string rostersFolder = settings.RostersSaveFolder;
            
            if (!Directory.Exists(rostersFolder))
            {
                Directory.CreateDirectory(rostersFolder);
            }
            
            string fileName = $"{_roster.RosterName}_{DateTime.Now:yyyyMMdd_HHmmss}.json";
            string filePath = Path.Combine(rostersFolder, fileName);
            
            _roster.SaveToFile(filePath);
            
            SaveConfirmationInfoBar.IsOpen = true;
        }

        private async void UnitList_DoubleTapped(object sender, DoubleTappedRoutedEventArgs e)
        {
            if (e.OriginalSource is FrameworkElement element && element.DataContext is Unit unit)
            {
                ContentDialog dialog = new ContentDialog { Title = unit.Name, CloseButtonText = "Close", XamlRoot = this.XamlRoot };
                
                StackPanel content = new StackPanel { Spacing = 12 };
                
                // Add profiles (stat blocks)
                foreach (UnitProfile profile in unit.Profiles)
                {
                    TextBlock profileTitle = new TextBlock { Text = $"{profile.Name} ({profile.TypeName})", FontWeight = FontWeights.Bold };
                    content.Children.Add(profileTitle);
                    
                    foreach (KeyValuePair<string, string> kvp in profile.Characteristics)
                    {
                        TextBlock stat = new TextBlock { Text = $"{kvp.Key}: {kvp.Value}", Margin = new Thickness(12, 0, 0, 0) };
                        content.Children.Add(stat);
                    }
                }
                
                // Add abilities
                if (unit.Abilities.Count > 0)
                {
                    TextBlock abilitiesTitle = new TextBlock { Text = "Abilities", FontWeight = FontWeights.Bold, Margin = new Thickness(0, 8, 0, 0) };
                    content.Children.Add(abilitiesTitle);
                    
                    foreach (UnitAbility ability in unit.Abilities)
                    {
                        TextBlock abilityText = new TextBlock { Text = $"{ability.Name}: {ability.Description}", TextWrapping = TextWrapping.Wrap, Margin = new Thickness(12, 4, 0, 0) };
                        content.Children.Add(abilityText);
                    }
                }
                
                ScrollViewer scrollViewer = new ScrollViewer {  Content = content, MaxHeight = 500 };
                
                dialog.Content = scrollViewer;
                await dialog.ShowAsync();
            }
        }

        private void LoadSavedRosters()
        {
            SavedRosters.Clear();
            
            AppSettings settings = AppSettings.Instance;
            string rostersFolder = settings.RostersSaveFolder;

            if (!Directory.Exists(rostersFolder))
            {
                Directory.CreateDirectory(rostersFolder);
                return;
            }

            string[] files = Directory.GetFiles(rostersFolder, "*.json");
            
            foreach (string filePath in files)
            {
                ArmyRosterViewModel? roster = ArmyRosterViewModel.LoadFromFile(filePath);
                if (roster != null)
                {
                    SavedRosters.Add(roster);
                }
            }
        }

        private async void NewRosterFromList_Click(object sender, RoutedEventArgs e)
        {
            NewRosterDialog dialog = new NewRosterDialog();
            dialog.XamlRoot = this.XamlRoot;
            
            ContentDialogResult result = await dialog.ShowAsync();
            
            if (result == ContentDialogResult.Primary && dialog.proposedRoster != null)
            {
                _roster = dialog.proposedRoster;
                LoadArmyCatalog();
                Bindings.Update();
            }
        }

        private void LoadSelectedRoster_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button button && button.DataContext is ArmyRosterViewModel selectedRoster)
            {
                _roster = selectedRoster;
                LoadArmyCatalog();
                Bindings.Update();
            }
        }
    }
}