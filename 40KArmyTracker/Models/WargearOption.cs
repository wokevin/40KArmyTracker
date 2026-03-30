using System.Collections.Generic;

namespace GW40KArmyTracker.Models
{
    public class WargearOption
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string GroupName { get; set; } = string.Empty;
        public int PointsCost { get; set; }
        public bool IsDefault { get; set; }
        public List<UnitProfile> Profiles { get; set; } = new();
    }
}