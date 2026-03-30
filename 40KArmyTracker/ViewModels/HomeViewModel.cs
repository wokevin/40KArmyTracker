namespace GW40KArmyTracker.ViewModels
{
    public sealed class HomeViewModel : ObservableObject
    {
        private string _welcomeText = "Welcome to 40KArmyTracker";
        public string WelcomeText
        {
            get => _welcomeText;
            set => SetProperty(ref _welcomeText, value);
        }
    }
}