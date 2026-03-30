using System.Collections.Generic;

namespace GW40KArmyTracker.Models
{
    public class Unit
    {
        public string Id { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public int PointsCost { get; set; }
        public List<string> Keywords { get; set; } = new();
        public List<string> CategoryIds { get; set; } = new();
        public List<UnitProfile> Profiles { get; set; } = new();
        public List<UnitAbility> Abilities { get; set; } = new();
        public List<WargearOption> WargearOptions { get; set; } = new();
    }
}