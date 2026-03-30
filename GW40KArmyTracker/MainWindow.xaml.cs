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

        private void RootNavView_Loaded(object sender, RoutedEventArgs e)
        {
            RootNavView.SelectedItem = RootNavView.MenuItems[0];
            Navigate("home");
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

        private void RootNavView_BackRequested(NavigationView sender, NavigationViewBackRequestedEventArgs args)
        {
            if (ContentFrame.CanGoBack)
            {
                ContentFrame.GoBack();
            }
        }

        private void Navigate(string tag)
        {
            System.Type pageType = tag switch
            {
                "home" => typeof(HomePage),
                "rosters" => typeof(RostersPage),
                "armies" => typeof(ArmiesPage),
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