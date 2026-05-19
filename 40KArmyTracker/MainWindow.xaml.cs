using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.Pages;

namespace GW40KArmyTracker
{
    public sealed partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();
        }

        private async void RootNavView_Loaded(object sender, RoutedEventArgs e)
        {
            // Default route
            RootNavView.SelectedItem = RootNavView.MenuItems[0];
            Navigate("home");

            // Preload factions at startup
            await Services.BattleScribeParser.Instance.GetFactionsAsync();
        }

        private void RootNavView_ItemInvoked(NavigationView sender, NavigationViewItemInvokedEventArgs args)
        {
            if (args.IsSettingsInvoked)
            {
                Navigate("settings");
                return;
            }

            if (args.InvokedItemContainer is NavigationViewItem nvi && nvi.Tag is string tag)
            {
                Navigate(tag);
            }
        }

        private void Navigate(string tag)
        {
            var pageType = tag switch
            {
                "home" => typeof(HomePage),
                "rosters" => typeof(RosterEditorPage),
                "armies" => typeof(ArmiesPage),
                "units" => typeof(UnitsPage),
                "settings" => typeof(SettingsPage),
                _ => typeof(HomePage)
            };

            if (ContentFrame.CurrentSourcePageType != pageType)
            {
                ContentFrame.Navigate(pageType);
            }
        }
    }
}
