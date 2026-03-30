using System;
using System.Collections.Generic;

namespace GW40KArmyTracker.Models
{
    public class Roster
    {
        public string Id { get; set; } = Guid.NewGuid().ToString();
        public string Name { get; set; } = "New Roster";
        public string Faction { get; set; } = string.Empty;
        public string Detachment { get; set; } = string.Empty;
        public int PointsLimit { get; set; } = 2000;
        public int CurrentPoints => CalculatePoints();
        public List<RosterUnit> Units { get; set; } = new();
        public DateTime CreatedAt { get; set; } = DateTime.Now;
        public DateTime ModifiedAt { get; set; } = DateTime.Now;

        private int CalculatePoints()
        {
            int total = 0;
            foreach (RosterUnit unit in Units)
            {
                total += unit.TotalPoints;
            }
            return total;
        }
    }

    public class RosterUnit
    {
        public string UnitId { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public int BasePoints { get; set; }
        public int ModelCount { get; set; } = 1;
        public List<RosterEnhancement> Enhancements { get; set; } = new();
        public int TotalPoints => BasePoints + EnhancementPoints;

        private int EnhancementPoints
        {
            get
            {
                int total = 0;
                foreach (RosterEnhancement e in Enhancements)
                {
                    total += e.Points;
                }
                return total;
            }
        }
    }

    public class RosterEnhancement
    {
        public string Name { get; set; } = string.Empty;
        public int Points { get; set; }
    }
}