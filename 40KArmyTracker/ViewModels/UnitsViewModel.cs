namespace GW40KArmyTracker.ViewModels
{
    public sealed class UnitsViewModel : ObservableObject
    {
        private string _title = "Units";
        public string Title
        {
            get => _title;
            set => SetProperty(ref _title, value);
        }
    }
}