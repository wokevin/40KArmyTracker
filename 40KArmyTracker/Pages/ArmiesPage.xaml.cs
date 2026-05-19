using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.Models;
using GW40KArmyTracker.ViewModels;

namespace GW40KArmyTracker.Pages
{
    public sealed partial class ArmiesPage : Page
    {
        private readonly ArmiesViewModel _viewModel;

        public ArmiesPage()
        {
            InitializeComponent();
            _viewModel = new ArmiesViewModel();
            DataContext = _viewModel;

            _viewModel.PropertyChanged += ViewModel_PropertyChanged;
        }

        private void ViewModel_PropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(ArmiesViewModel.HasDescription))
            {
                UpdateDescriptionVisibility();
            }
            else if (e.PropertyName == nameof(ArmiesViewModel.HasStatBlock))
            {
                UpdateStatBlockVisibility();
            }
        }

        private void RefreshButton_Click(object sender, RoutedEventArgs e)
        {
            _viewModel.Refresh();
            UpdateAllVisibility();
        }

        private void CatalogListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (sender is ListView listView && listView.SelectedItem is Catalog selectedCatalog)
            {
                _viewModel.SelectedCatalog = selectedCatalog;
            }
            UpdateAllVisibility();
        }

        private void CategoryListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (CategoryListView.SelectedItem is Category selectedCategory)
            {
                _viewModel.SelectedCategory = selectedCategory;
            }
            UpdateAllVisibility();
        }

        private void UnitsListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (UnitsListView.SelectedItem is Unit selectedUnit)
            {
                _viewModel.SelectedUnit = selectedUnit;
            }
            UpdateAllVisibility();
        }

        private void WargearListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _viewModel.UpdateSelectedWargear(WargearListView.SelectedItems);
            UpdateDescriptionVisibility();
        }

        private void FactionRulesListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (FactionRulesListView.SelectedItem is UnitAbility selectedRule)
            {
                _viewModel.SelectedFactionRule = selectedRule;
            }
            UpdateDescriptionVisibility();
        }

        private void SharedRulesListView_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (SharedRulesListView.SelectedItem is UnitAbility selectedRule)
            {
                _viewModel.SelectedSharedRule = selectedRule;
            }
            UpdateDescriptionVisibility();
        }

        private void UpdateAllVisibility()
        {
            UpdateUnitDetailsVisibility();
            UpdateStatBlockVisibility();
            UpdateDescriptionVisibility();
        }

        private void UpdateUnitDetailsVisibility()
        {
            bool hasUnit = _viewModel.SelectedUnit != null;
            NoUnitSelectedPanel.Visibility = hasUnit ? Visibility.Collapsed : Visibility.Visible;
            UnitDetailsPanel.Visibility = hasUnit ? Visibility.Visible : Visibility.Collapsed;
        }

        private void UpdateStatBlockVisibility()
        {
            StatBlockPanel.Visibility = _viewModel.HasStatBlock ? Visibility.Visible : Visibility.Collapsed;
        }

        private void UpdateDescriptionVisibility()
        {
            DescriptionPanel.Visibility = _viewModel.HasDescription ? Visibility.Visible : Visibility.Collapsed;
        }
    }
}