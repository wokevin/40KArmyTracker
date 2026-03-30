using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.ViewModels;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class HomePage : Page
    {
        public HomePage()
        {
            InitializeComponent();
            DataContext = new HomeViewModel();
        }
    }
}