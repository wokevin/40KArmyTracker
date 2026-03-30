using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace GW40KArmyTracker.ViewModels
{
    internal class ArmyRosterViewModel
    {
        //  Set to a default sentinal value of -1 to indicate that the point limit has not been set.
        private int mPointLimit = -1;
        protected int PointLimit
        {
            get => mPointLimit;
            set
            {
                if (value < 0)
                    throw new ArgumentOutOfRangeException(nameof(PointLimit), "Point limit must be a non-negative integer.");
                mPointLimit = value;
            }
        }

        private List<object> mArmyList = new List<object>();
        protected List<object> ArmyList
        {
            set
            {
                if (value == null)
                    throw new ArgumentNullException(nameof(ArmyList), "Army list cannot be null.");
                mArmyList = value;
            }
        }
        public List<object> GetArmyList() => mArmyList;

    }
}
