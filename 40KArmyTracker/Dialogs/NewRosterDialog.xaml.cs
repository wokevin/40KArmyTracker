using System;
using System.Collections.Generic;
using System.IO;
using System.Xml.Serialization;
using Microsoft.UI.Xaml.Controls;
using GW40KArmyTracker.ViewModels;
using GW40KArmyTracker.Services;
using GW40KArmyTracker.Models;

namespace GW40KArmyTracker.Dialogs
{
    public sealed partial class NewRosterDialog : ContentDialog
    {
        internal ArmyRosterViewModel? proposedRoster { get; private set; }

        public NewRosterDialog()
        {
            this.InitializeComponent();
            LoadArmies();
        }

        private async void LoadArmies()
        {
            ArmyComboBox.Items.Clear();
            foreach (string factionName in await BattleScribeParser.Instance.GetFactionsAsync())
            {
                ComboBoxItem item = new ComboBoxItem { Content = factionName };
                ArmyComboBox.Items.Add(item);
            }
        }

        private void CreateButton_Click(ContentDialog sender, ContentDialogButtonClickEventArgs args)
        {
            string rosterName = RosterNameTextBox.Text;
            string armyName = (ArmyComboBox.SelectedItem as ComboBoxItem)?.Content?.ToString();
            int pointLimit = (int)PointLimitNumberBox.Value;

            if (string.IsNullOrWhiteSpace(rosterName) || string.IsNullOrWhiteSpace(armyName))
            {
                args.Cancel = true;
                return;
            }

            ArmyRosterViewModel viewModel = new ArmyRosterViewModel();
            viewModel.CreateNewRoster(rosterName, armyName, pointLimit);

            SaveRoster(viewModel);
            proposedRoster = viewModel;
        }

        private void SaveRoster(ArmyRosterViewModel roster)
        {
            string rostersFolder = AppSettings.Instance.RostersSaveFolder;
            
            if (!Directory.Exists(rostersFolder))
            {
                Directory.CreateDirectory(rostersFolder);
            }

            string fileName = $"{roster.RosterName}_{DateTime.Now:yyyyMMdd_HHmmss}.xml";
            string filePath = Path.Combine(rostersFolder, fileName);

            XmlSerializer serializer = new XmlSerializer(typeof(ArmyRosterViewModel));
            using (StreamWriter writer = new StreamWriter(filePath))
            {
                serializer.Serialize(writer, roster);
            }
        }
    }
}