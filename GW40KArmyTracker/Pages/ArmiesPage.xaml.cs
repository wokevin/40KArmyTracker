using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.ViewModels;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class ArmiesPage : Page
    {
        public ArmiesPage()
        {
            InitializeComponent();
            DataContext = new ArmiesViewModel();
        }
    }
}