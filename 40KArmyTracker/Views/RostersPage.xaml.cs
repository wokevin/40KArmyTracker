using System;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.Dialogs;

namespace GW40KArmyTracker.Views
{
    public sealed partial class RostersPage : Page
    {
        public RostersPage()
        {
            this.InitializeComponent();
        }

        private async void NewRoster_Click(object sender, RoutedEventArgs e)
        {
            NewRosterDialog dialog = new NewRosterDialog();
            dialog.XamlRoot = this.XamlRoot;
            await dialog.ShowAsync();
        }
    }
}