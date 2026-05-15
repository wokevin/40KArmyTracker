using Microsoft.UI.Xaml;

namespace GW40KArmyTracker
{
    public partial class App : Application
    {
        public static Window? MainWindow { get; private set; }

        public App()
        {
            InitializeComponent();
        }

        protected override async void OnLaunched(LaunchActivatedEventArgs args)
        {
            MainWindow = new MainWindow();
            MainWindow.Activate();
            
            // Preload factions at startup
            await Services.BattleScribeParser.Instance.GetFactionsAsync();
        }
    }
}
