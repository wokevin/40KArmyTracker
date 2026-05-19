using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace GW40KArmyTracker.ViewModels
{
    internal class ArmyRosterViewModel
    {
        public class Selection
        {
            public string Reference { get; set; }
            public int Count { get; set; }
            public int Points { get; set; }
        }

        public string RosterName { get; set; }
        public string ArmyName { get; set; }
        public string SuperCategory { get; set; }  // NEW: Store the super category (Imperium/Chaos/Xenos)

        //  Set to a default sentinal value of -1 to indicate that the point limit has not been set.
        private int mPointLimit = -1;
        public int PointLimit
        {
            get => mPointLimit;
            set
            {
                if (value < 0)
                    throw new ArgumentOutOfRangeException(nameof(PointLimit), "Point limit must be a non-negative integer.");
                mPointLimit = value;
            }
        }

        private List<Selection> mArmyList = new List<Selection>();
        protected List<Selection> ArmyList
        {
            set
            {
                if (value == null)
                    throw new ArgumentNullException(nameof(ArmyList), "Army list cannot be null.");
                mArmyList = value;
            }
        }
        public List<Selection> GetArmyList() => mArmyList;

        public int TotalPoints => mArmyList.Sum(selection => selection.Points * selection.Count);

        public void CreateNewRoster(string rosterName, string armyName, string superCategory, int pointLimit)
        {
            RosterName = rosterName;
            ArmyName = armyName;
            SuperCategory = superCategory;  // NEW: Store super category
            PointLimit = pointLimit;
            mArmyList.Clear();
        }

        public void AddSelection(string reference, int count, int points)
        {
            Selection selection = new Selection 
            { 
                Reference = reference, 
                Count = count, 
                Points = points 
            };
            mArmyList.Add(selection);
        }

        public void RemoveSelection(Selection selection)
        {
            mArmyList.Remove(selection);
        }

        public void UpdateSelectionCount(Selection selection, int newCount)
        {
            if (newCount <= 0)
            {
                RemoveSelection(selection);
            }
            else
            {
                selection.Count = newCount;
            }
        }

        public void ClearArmy()
        {
            mArmyList.Clear();
        }

        public int RemainingPoints => PointLimit >= 0 ? PointLimit - TotalPoints : -1;

        public static ArmyRosterViewModel? LoadFromFile(string filePath)
        {
            if (!File.Exists(filePath))
                return null;

            try
            {
                string json = File.ReadAllText(filePath);
                return JsonSerializer.Deserialize<ArmyRosterViewModel>(json);
            }
            catch
            {
                return null;
            }
        }

        public void SaveToFile(string filePath)
        {
            string? directory = Path.GetDirectoryName(filePath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            string json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(filePath, json);
        }
    }
}
