using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.ViewModels;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class SettingsPage : Page
    {
        public SettingsPage()
        {
            InitializeComponent();
            DataContext = new SettingsViewModel();
        }
    }
}