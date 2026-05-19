using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.Dialogs;
using GW40KArmyTracker.Pages;
using GW40KArmyTracker.ViewModels;
using System;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class HomePage : Page
    {
        public HomePage()
        {
            this.InitializeComponent();
            DataContext = new HomeViewModel();
        }

        private async void NewRoster_Click(object sender, RoutedEventArgs e)
        {
            NewRosterDialog dialog = new NewRosterDialog();
            dialog.XamlRoot = this.XamlRoot;
            ContentDialogResult result = await dialog.ShowAsync();

            if (result == ContentDialogResult.Primary && dialog.proposedRoster != null)
            {
                Frame.Navigate(typeof(RosterEditorPage), dialog.proposedRoster);
            }
        }
    }
}