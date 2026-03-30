using System.Collections.Generic;

namespace GW40KArmyTracker.Models
{
    public class UnitProfile
    {
        public string Name { get; set; } = string.Empty;
        public string TypeName { get; set; } = string.Empty;
        public Dictionary<string, string> Characteristics { get; set; } = new();
    }
}