using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.ViewModels;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class UnitsPage : Page
    {
        public UnitsPage()
        {
            InitializeComponent();
            DataContext = new UnitsViewModel();
        }
    }
}   