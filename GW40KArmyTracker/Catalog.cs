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
    }

    public class Unit
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public int PointsCost { get; set; }
        public List<string> Keywords { get; set; } = new();
        public List<UnitProfile> Profiles { get; set; } = new();
    }

    public class UnitProfile
    {
        public string Name { get; set; } = string.Empty;
        public Dictionary<string, string> Characteristics { get; set; } = new();
    }
}