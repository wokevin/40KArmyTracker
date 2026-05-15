using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Navigation;
using GW40KArmyTracker.ViewModels;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class RosterEditorPage : Page
    {
        internal ArmyRosterViewModel Roster { get; private set; }   

        // Public properties for XAML binding
        public string RosterName => Roster?.RosterName ?? string.Empty;
        public string ArmyName => Roster?.ArmyName ?? string.Empty;
        public int TotalPoints => Roster?.TotalPoints ?? 0;
        public int PointLimit => Roster?.PointLimit ?? 0;

        public RosterEditorPage()
        {
            this.InitializeComponent();
            Roster = new ArmyRosterViewModel(); // Temp placeholder to avoid binding errors
        }

        protected override void OnNavigatedTo(NavigationEventArgs e)
        {
            base.OnNavigatedTo(e);

            if (e.Parameter is ArmyRosterViewModel roster)
            {
                Roster = roster;
                Bindings.Update(); // Force bindings to refresh
                // TODO: Load the army catalog and units for this roster
            }
        }
    }
}