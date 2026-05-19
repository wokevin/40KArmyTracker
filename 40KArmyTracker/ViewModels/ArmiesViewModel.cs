using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using GW40KArmyTracker.Models;
using GW40KArmyTracker.Services;

namespace GW40KArmyTracker.ViewModels
{
    public sealed class ArmiesViewModel : ObservableObject
    {
        private readonly BattleScribeParser _parser;
        private readonly AppSettings _settings;
        private List<Unit> _allUnitsInCatalog = new();

        public ArmiesViewModel()
        {
            _settings = AppSettings.Instance;
            _parser = BattleScribeParser.Instance;

            Catalogs = new ObservableCollection<Catalog>();
            Categories = new ObservableCollection<Category>();
            Units = new ObservableCollection<Unit>();
            WargearOptions = new ObservableCollection<WargearOption>();
            FactionRules = new ObservableCollection<UnitAbility>();
            SharedRules = new ObservableCollection<UnitAbility>();
            SelectedWargear = new List<WargearOption>();

            LoadCatalogs();
        }

        public ObservableCollection<Catalog> Catalogs { get; }
        public ObservableCollection<CatalogGroup> GroupedCatalogs { get; } = new ObservableCollection<CatalogGroup>();
        public ObservableCollection<Category> Categories { get; }
        public ObservableCollection<Unit> Units { get; }
        public ObservableCollection<WargearOption> WargearOptions { get; }
        public ObservableCollection<UnitAbility> FactionRules { get; }
        public ObservableCollection<UnitAbility> SharedRules { get; }
        public List<WargearOption> SelectedWargear { get; }

        private Catalog? _selectedCatalog;
        public Catalog? SelectedCatalog
        {
            get => _selectedCatalog;
            set
            {
                if (SetProperty(ref _selectedCatalog, value))
                {
                    LoadCategoriesAndUnits();
                }
            }
        }

        private Category? _selectedCategory;
        public Category? SelectedCategory
        {
            get => _selectedCategory;
            set
            {
                if (SetProperty(ref _selectedCategory, value))
                {
                    FilterUnitsByCategory();
                }
            }
        }

        private Unit? _selectedUnit;
        public Unit? SelectedUnit
        {
            get => _selectedUnit;
            set
            {
                if (SetProperty(ref _selectedUnit, value))
                {
                    LoadWargearForUnit();
                    UpdateUnitDetails();
                }
            }
        }

        private WargearOption? _selectedWargearItem;
        public WargearOption? SelectedWargearItem
        {
            get => _selectedWargearItem;
            set
            {
                if (SetProperty(ref _selectedWargearItem, value))
                {
                    UpdateSelectedItemDescription();
                }
            }
        }

        private UnitAbility? _selectedFactionRule;
        public UnitAbility? SelectedFactionRule
        {
            get => _selectedFactionRule;
            set
            {
                if (SetProperty(ref _selectedFactionRule, value))
                {
                    UpdateFactionRuleDescription();
                }
            }
        }

        private UnitAbility? _selectedSharedRule;
        public UnitAbility? SelectedSharedRule
        {
            get => _selectedSharedRule;
            set
            {
                if (SetProperty(ref _selectedSharedRule, value))
                {
                    UpdateSharedRuleDescription();
                }
            }
        }

        public string SelectedUnitName => _selectedUnit?.Name ?? string.Empty;
        public int SelectedUnitBaseCost => _selectedUnit?.PointsCost ?? 0;
        public string SelectedUnitKeywords => _selectedUnit != null ? string.Join(", ", _selectedUnit.Keywords) : string.Empty;
        public bool HasSelectedUnit => _selectedUnit != null;

        private string _statBlock = string.Empty;
        public string StatBlock
        {
            get => _statBlock;
            set => SetProperty(ref _statBlock, value);
        }

        public bool HasStatBlock => !string.IsNullOrEmpty(_statBlock);

        private string _selectedItemName = string.Empty;
        public string SelectedItemName
        {
            get => _selectedItemName;
            set => SetProperty(ref _selectedItemName, value);
        }

        private string _selectedItemDescription = string.Empty;
        public string SelectedItemDescription
        {
            get => _selectedItemDescription;
            set => SetProperty(ref _selectedItemDescription, value);
        }

        public bool HasDescription => !string.IsNullOrEmpty(_selectedItemDescription);

        private int _totalCost;
        public int TotalCost
        {
            get => _totalCost;
            set => SetProperty(ref _totalCost, value);
        }

        private bool _hasNoCatalogs;
        public bool HasNoCatalogs
        {
            get => _hasNoCatalogs;
            set => SetProperty(ref _hasNoCatalogs, value);
        }

        private string _statusMessage = string.Empty;
        public string StatusMessage
        {
            get => _statusMessage;
            set => SetProperty(ref _statusMessage, value);
        }

        public void LoadCatalogs()
        {
            Catalogs.Clear();
            Categories.Clear();
            Units.Clear();
            WargearOptions.Clear();
            SelectedWargear.Clear();
            _allUnitsInCatalog.Clear();
            _selectedUnit = null;
            _selectedCatalog = null;
            _selectedCategory = null;
            _selectedWargearItem = null;
            TotalCost = 0;
            ClearDetails();

            if (string.IsNullOrEmpty(_settings.DefaultDataSourceFolder))
            {
                HasNoCatalogs = true;
                StatusMessage = "No data folder configured. Go to Settings to select your BattleScribe data folder.";
                return;
            }

            List<Catalog> loadedCatalogs = _parser.LoadCatalogsFromFolder(_settings.DefaultDataSourceFolder);

            if (loadedCatalogs.Count == 0)
            {
                HasNoCatalogs = true;
                StatusMessage = $"No .cat or .catz files found in: {_settings.DefaultDataSourceFolder}";
                return;
            }

            foreach (Catalog catalog in loadedCatalogs)
            {
                Catalogs.Add(catalog);
            }

            HasNoCatalogs = false;
            StatusMessage = $"Loaded {Catalogs.Count} catalog(s) with {Catalogs.Sum(c => c.Units.Count)} total units.";

            // Group catalogs by SuperCategory
            GroupedCatalogs.Clear();
            IEnumerable<IGrouping<string, Catalog>> grouped = loadedCatalogs
                .GroupBy(c => c.SuperCategory)
                .OrderBy(g => g.Key);

            foreach (IGrouping<string, Catalog> group in grouped)
            {
                CatalogGroup catalogGroup = new CatalogGroup
                {
                    SuperCategory = group.Key
                };
                
                foreach (Catalog catalog in group.OrderBy(c => c.Name))
                {
                    catalogGroup.Catalogs.Add(catalog);
                }
                
                GroupedCatalogs.Add(catalogGroup);
            }
        }

        private void LoadCategoriesAndUnits()
        {
            Categories.Clear();
            Units.Clear();
            WargearOptions.Clear();
            FactionRules.Clear();
            SharedRules.Clear();
            SelectedWargear.Clear();
            _allUnitsInCatalog.Clear();
            _selectedUnit = null;
            _selectedCategory = null;
            _selectedWargearItem = null;
            _selectedFactionRule = null;
            _selectedSharedRule = null;
            TotalCost = 0;
            ClearDetails();
            NotifyUnitChanged();

            if (_selectedCatalog == null)
                return;

            _allUnitsInCatalog = _selectedCatalog.Units.ToList();

            Categories.Add(new Category { Id = "all", Name = "All Units", IsFaction = false });

            foreach (Category cat in _selectedCatalog.Categories)
            {
                bool hasUnits = _allUnitsInCatalog.Any(u => u.CategoryIds.Contains(cat.Id));
                if (hasUnits)
                {
                    Categories.Add(cat);
                }
            }

            foreach (Unit unit in _allUnitsInCatalog.OrderBy(u => u.Name))
            {
                Units.Add(unit);
            }

            foreach (UnitAbility rule in _selectedCatalog.FactionRules.OrderBy(r => r.Name))
            {
                FactionRules.Add(rule);
            }

            foreach (UnitAbility rule in _selectedCatalog.SharedRules.OrderBy(r => r.Name))
            {
                SharedRules.Add(rule);
            }
        }

        private void FilterUnitsByCategory()
        {
            Units.Clear();
            WargearOptions.Clear();
            SelectedWargear.Clear();
            _selectedUnit = null;
            _selectedWargearItem = null;
            TotalCost = 0;
            ClearDetails();
            NotifyUnitChanged();

            if (_selectedCatalog == null)
                return;

            IEnumerable<Unit> filteredUnits;

            if (_selectedCategory == null || _selectedCategory.Id == "all")
            {
                filteredUnits = _allUnitsInCatalog;
            }
            else
            {
                filteredUnits = _allUnitsInCatalog.Where(u => u.CategoryIds.Contains(_selectedCategory.Id));
            }

            foreach (Unit unit in filteredUnits.OrderBy(u => u.Name))
            {
                Units.Add(unit);
            }
        }

        private void LoadWargearForUnit()
        {
            WargearOptions.Clear();
            SelectedWargear.Clear();
            _selectedWargearItem = null;

            if (_selectedUnit != null)
            {
                foreach (WargearOption option in _selectedUnit.WargearOptions.OrderBy(w => w.GroupName).ThenBy(w => w.Name))
                {
                    WargearOptions.Add(option);
                }
            }

            CalculateTotalCost();
            NotifyUnitChanged();
        }

        public void UpdateSelectedWargear(IList<object> selectedItems)
        {
            SelectedWargear.Clear();
            WargearOption? lastSelected = null;

            foreach (object item in selectedItems)
            {
                if (item is WargearOption wargear)
                {
                    SelectedWargear.Add(wargear);
                    lastSelected = wargear;
                }
            }

            SelectedWargearItem = lastSelected;
            CalculateTotalCost();
        }

        private void CalculateTotalCost()
        {
            int baseCost = _selectedUnit?.PointsCost ?? 0;
            int wargearCost = SelectedWargear.Sum(w => w.PointsCost);
            TotalCost = baseCost + wargearCost;
        }

        private void UpdateUnitDetails()
        {
            BuildStatBlock();
            UpdateSelectedItemDescription();
        }

        private void BuildStatBlock()
        {
            if (_selectedUnit == null || _selectedUnit.Profiles.Count == 0)
            {
                StatBlock = string.Empty;
                OnPropertyChanged(nameof(HasStatBlock));
                return;
            }

            StringBuilder sb = new();

            foreach (UnitProfile profile in _selectedUnit.Profiles)
            {
                if (sb.Length > 0)
                    sb.AppendLine();

                if (!string.IsNullOrEmpty(profile.TypeName))
                {
                    sb.AppendLine($"[{profile.TypeName}] {profile.Name}");
                }
                else
                {
                    sb.AppendLine(profile.Name);
                }

                List<string> stats = new();
                foreach (KeyValuePair<string, string> stat in profile.Characteristics)
                {
                    stats.Add($"{stat.Key}: {stat.Value}");
                }
                sb.AppendLine(string.Join("  |  ", stats));
            }

            StatBlock = sb.ToString().TrimEnd();
            OnPropertyChanged(nameof(HasStatBlock));
        }

        private void UpdateSelectedItemDescription()
        {
            if (_selectedWargearItem != null)
            {
                SelectedItemName = _selectedWargearItem.Name;

                StringBuilder sb = new();

                if (_selectedWargearItem.Profiles.Count > 0)
                {
                    foreach (UnitProfile profile in _selectedWargearItem.Profiles)
                    {
                        if (sb.Length > 0)
                            sb.AppendLine();

                        sb.AppendLine($"[{profile.TypeName}] {profile.Name}");
                        List<string> stats = new();
                        foreach (KeyValuePair<string, string> stat in profile.Characteristics)
                        {
                            stats.Add($"{stat.Key}: {stat.Value}");
                        }
                        sb.AppendLine(string.Join("  |  ", stats));
                    }
                }

                if (!string.IsNullOrEmpty(_selectedWargearItem.Description))
                {
                    if (sb.Length > 0)
                        sb.AppendLine();
                    sb.AppendLine(_selectedWargearItem.Description);
                }

                if (sb.Length == 0)
                {
                    sb.AppendLine($"Group: {_selectedWargearItem.GroupName}");
                    sb.AppendLine($"Cost: +{_selectedWargearItem.PointsCost} pts");
                    if (_selectedWargearItem.IsDefault)
                    {
                        sb.AppendLine("(Default option)");
                    }
                }

                SelectedItemDescription = sb.ToString().TrimEnd();
            }
            else if (_selectedUnit != null)
            {
                SelectedItemName = _selectedUnit.Name;

                if (!string.IsNullOrEmpty(_selectedUnit.Description))
                {
                    SelectedItemDescription = _selectedUnit.Description;
                }
                else if (_selectedUnit.Abilities.Count > 0)
                {
                    StringBuilder sb = new();
                    foreach (UnitAbility ability in _selectedUnit.Abilities)
                    {
                        if (sb.Length > 0)
                            sb.AppendLine();
                        sb.AppendLine($"• {ability.Name}");
                        if (!string.IsNullOrEmpty(ability.Description))
                        {
                            sb.AppendLine($"  {ability.Description}");
                        }
                    }
                    SelectedItemDescription = sb.ToString().TrimEnd();
                }
                else
                {
                    SelectedItemDescription = string.Empty;
                }
            }
            else
            {
                ClearDetails();
            }

            OnPropertyChanged(nameof(HasDescription));
        }

        private void ClearDetails()
        {
            SelectedItemName = string.Empty;
            SelectedItemDescription = string.Empty;
            StatBlock = string.Empty;
            OnPropertyChanged(nameof(HasDescription));
            OnPropertyChanged(nameof(HasStatBlock));
        }

        private void NotifyUnitChanged()
        {
            OnPropertyChanged(nameof(SelectedUnitName));
            OnPropertyChanged(nameof(SelectedUnitBaseCost));
            OnPropertyChanged(nameof(SelectedUnitKeywords));
            OnPropertyChanged(nameof(HasSelectedUnit));
        }

        public void Refresh()
        {
            AppSettings.Reload();
            LoadCatalogs();
        }

        private void UpdateFactionRuleDescription()
        {
            if (_selectedFactionRule != null)
            {
                SelectedItemName = _selectedFactionRule.Name;
                SelectedItemDescription = _selectedFactionRule.Description;
                OnPropertyChanged(nameof(HasDescription));
            }
        }

        private void UpdateSharedRuleDescription()
        {
            if (_selectedSharedRule != null)
            {
                SelectedItemName = _selectedSharedRule.Name;
                SelectedItemDescription = _selectedSharedRule.Description;
                OnPropertyChanged(nameof(HasDescription));
            }
        }
    }
}