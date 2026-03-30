using System.Collections.Generic;

namespace GW40KArmyTracker.Models
{
    public class Catalog
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public string FilePath { get; set; } = string.Empty;
        public bool IsGameSystem { get; set; }
        public List<Unit> Units { get; set; } = new();
        public List<Category> Categories { get; set; } = new();
        public List<UnitAbility> FactionRules { get; set; } = new();
        public List<UnitAbility> SharedRules { get; set; } = new();
    }
}