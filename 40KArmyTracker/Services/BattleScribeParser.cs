using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Xml.Linq;
using GW40KArmyTracker.Models;

namespace GW40KArmyTracker.Services
{
    public class BattleScribeParser
    {
        private static readonly XNamespace CatNs = "http://www.battlescribe.net/schema/catalogueSchema";
        private static readonly XNamespace GstNs = "http://www.battlescribe.net/schema/gameSystemSchema";

        private Dictionary<string, Category> _gameSystemCategories = new();

        private const string ExclusionKeyword = "Faction";

        public List<Catalog> LoadCatalogsFromFolder(string folderPath)
        {
            List<Catalog> catalogs = new();
            _gameSystemCategories.Clear();

            if (string.IsNullOrEmpty(folderPath) || !Directory.Exists(folderPath))
                return catalogs;

            foreach (string file in Directory.GetFiles(folderPath, "*.gst"))
            {
                ParseGameSystemFile(file);
            }
            foreach (string file in Directory.GetFiles(folderPath, "*.gstz"))
            {
                ParseCompressedGameSystemFile(file);
            }

            foreach (string file in Directory.GetFiles(folderPath, "*.cat"))
            {
                Catalog? catalog = ParseCatalogFile(file);
                if (catalog != null && catalog.Units.Count > 0)
                    catalogs.Add(catalog);
            }

            foreach (string file in Directory.GetFiles(folderPath, "*.catz"))
            {
                Catalog? catalog = ParseCompressedCatalogFile(file);
                if (catalog != null && catalog.Units.Count > 0)
                    catalogs.Add(catalog);
            }

            return catalogs.OrderBy(c => c.Name).ToList();
        }

        public List<Category> GetBattlefieldRoles()
        {
            return _gameSystemCategories.Values
                .Where(c => !c.IsFaction)
                .OrderBy(c => c.Name)
                .ToList();
        }

        private void ParseGameSystemFile(string filePath)
        {
            try
            {
                XDocument doc = XDocument.Load(filePath);
                ParseCategoriesFromDocument(doc);
            }
            catch
            {
            }
        }

        private void ParseCompressedGameSystemFile(string filePath)
        {
            try
            {
                using FileStream fileStream = File.OpenRead(filePath);
                using ZipArchive archive = new(fileStream, ZipArchiveMode.Read);

                ZipArchiveEntry? entry = archive.Entries.FirstOrDefault(e =>
                    e.Name.EndsWith(".gst", StringComparison.OrdinalIgnoreCase));

                if (entry != null)
                {
                    using Stream entryStream = entry.Open();
                    XDocument doc = XDocument.Load(entryStream);
                    ParseCategoriesFromDocument(doc);
                }
            }
            catch
            {
            }
        }

        private void ParseCategoriesFromDocument(XDocument doc)
        {
            XElement? root = doc.Root;
            if (root == null)
                return;

            XNamespace ns = GstNs;

            XElement? categoryEntries = root.Element(ns + "categoryEntries");
            if (categoryEntries == null)
                return;

            foreach (XElement catElement in categoryEntries.Elements())
            {
                if (catElement.Name.LocalName != "categoryEntry")
                    continue;

                string? id = catElement.Attribute("id")?.Value;
                string? name = catElement.Attribute("name")?.Value;

                if (string.IsNullOrEmpty(id) || string.IsNullOrEmpty(name))
                    continue;

                bool isFaction = name.StartsWith("Faction:", StringComparison.OrdinalIgnoreCase) ||
                                 name.Contains(ExclusionKeyword) ||
                                 catElement.Attribute("hidden")?.Value == "true";

                Category category = new()
                {
                    Id = id,
                    Name = name,
                    IsFaction = isFaction
                };

                _gameSystemCategories[id] = category;
            }
        }

        private Catalog? ParseCatalogFile(string filePath)
        {
            try
            {
                XDocument doc = XDocument.Load(filePath);
                return ParseCatalogXml(doc, filePath);
            }
            catch
            {
                return null;
            }
        }

        private Catalog? ParseCompressedCatalogFile(string filePath)
        {
            try
            {
                using FileStream fileStream = File.OpenRead(filePath);
                using ZipArchive archive = new(fileStream, ZipArchiveMode.Read);

                ZipArchiveEntry? entry = archive.Entries.FirstOrDefault(e =>
                    e.Name.EndsWith(".cat", StringComparison.OrdinalIgnoreCase) ||
                    e.Name.EndsWith(".gst", StringComparison.OrdinalIgnoreCase));

                if (entry == null)
                    return null;

                using Stream entryStream = entry.Open();
                XDocument doc = XDocument.Load(entryStream);
                return ParseCatalogXml(doc, filePath);
            }
            catch
            {
                return null;
            }
        }

        private Catalog? ParseCatalogXml(XDocument doc, string filePath)
        {
            XElement? root = doc.Root;
            if (root == null)
                return null;

            XNamespace ns = root.Name.LocalName == "gameSystem" ? GstNs : CatNs;

            Catalog catalog = new()
            {
                Id = root.Attribute("id")?.Value ?? Guid.NewGuid().ToString(),
                Name = root.Attribute("name")?.Value ?? Path.GetFileNameWithoutExtension(filePath),
                FilePath = filePath,
                IsGameSystem = root.Name.LocalName == "gameSystem"
            };

            catalog.Categories = _gameSystemCategories.Values
                .Where(c => !c.IsFaction)
                .OrderBy(c => c.Name)
                .ToList();

            // Parse Faction Rules and Shared Rules
            ParseFactionAndSharedRules(root, ns, catalog);

            HashSet<string> addedUnitIds = new();

            XElement? sharedSelectionEntries = root.Element(ns + "sharedSelectionEntries")
                ?? root.Element(CatNs + "sharedSelectionEntries");

            if (sharedSelectionEntries != null)
            {
                foreach (XElement entry in sharedSelectionEntries.Elements())
                {
                    if (entry.Name.LocalName != "selectionEntry")
                        continue;

                    string? type = entry.Attribute("type")?.Value;
                    string? id = entry.Attribute("id")?.Value;

                    if ((type == "unit" || type == "model") && !string.IsNullOrEmpty(id) && !addedUnitIds.Contains(id))
                    {
                        Unit unit = ParseUnit(entry, ns);
                        if (!string.IsNullOrEmpty(unit.Name))
                        {
                            catalog.Units.Add(unit);
                            addedUnitIds.Add(id);
                        }
                    }
                }
            }

            return catalog;
        }

        private void ParseFactionAndSharedRules(XElement root, XNamespace ns, Catalog catalog)
        {
            // Parse sharedRules element
            XElement? sharedRules = root.Element(ns + "sharedRules") ?? root.Element(CatNs + "sharedRules");
            if (sharedRules != null)
            {
                foreach (XElement rule in sharedRules.Elements())
                {
                    if (rule.Name.LocalName != "rule")
                        continue;

                    string? name = rule.Attribute("name")?.Value;
                    string? description = rule.Element(ns + "description")?.Value
                        ?? rule.Element(CatNs + "description")?.Value;

                    if (!string.IsNullOrEmpty(name))
                    {
                        UnitAbility sharedRule = new()
                        {
                            Name = name,
                            Description = description?.Trim() ?? string.Empty
                        };
                        catalog.SharedRules.Add(sharedRule);
                    }
                }
            }

            // Parse sharedProfiles for faction abilities
            XElement? sharedProfiles = root.Element(ns + "sharedProfiles") ?? root.Element(CatNs + "sharedProfiles");
            if (sharedProfiles != null)
            {
                foreach (XElement profile in sharedProfiles.Elements())
                {
                    if (profile.Name.LocalName != "profile")
                        continue;

                    string? typeName = profile.Attribute("typeName")?.Value ?? string.Empty;

                    if (typeName.Contains("Abilities") || typeName.Contains("Ability") ||
                        typeName.Contains("Detachment") || typeName.Contains("Rule"))
                    {
                        UnitAbility ability = ParseAbility(profile, ns);
                        if (!string.IsNullOrEmpty(ability.Name) &&
                            !catalog.FactionRules.Any(r => r.Name == ability.Name))
                        {
                            catalog.FactionRules.Add(ability);
                        }
                    }
                }
            }

            // Also check for rules directly on the root (for faction-specific rules)
            XElement? rules = root.Element(ns + "rules") ?? root.Element(CatNs + "rules");
            if (rules != null)
            {
                foreach (XElement rule in rules.Elements())
                {
                    if (rule.Name.LocalName != "rule")
                        continue;

                    string? name = rule.Attribute("name")?.Value;
                    string? description = rule.Element(ns + "description")?.Value
                        ?? rule.Element(CatNs + "description")?.Value;

                    if (!string.IsNullOrEmpty(name) && !catalog.FactionRules.Any(r => r.Name == name))
                    {
                        UnitAbility factionRule = new()
                        {
                            Name = name,
                            Description = description?.Trim() ?? string.Empty
                        };
                        catalog.FactionRules.Add(factionRule);
                    }
                }
            }
        }

        private Unit ParseUnit(XElement entry, XNamespace ns)
        {
            Unit unit = new()
            {
                Id = entry.Attribute("id")?.Value ?? Guid.NewGuid().ToString(),
                Name = entry.Attribute("name")?.Value ?? "Unknown Unit"
            };

            unit.PointsCost = GetDirectPointsCost(entry, ns);

            ParseProfiles(entry, ns, unit);

            XElement? selectionEntries = entry.Element(ns + "selectionEntries")
                ?? entry.Element(CatNs + "selectionEntries");
            if (selectionEntries != null)
            {
                foreach (XElement subEntry in selectionEntries.Elements())
                {
                    if (subEntry.Name.LocalName == "selectionEntry")
                    {
                        ParseProfiles(subEntry, ns, unit);
                    }
                }
            }

            if (unit.Abilities.Count > 0)
            {
                unit.Description = string.Join("\n\n", unit.Abilities.Select(a => $"{a.Name}: {a.Description}"));
            }

            XElement? categoryLinks = entry.Element(ns + "categoryLinks") ?? entry.Element(CatNs + "categoryLinks");
            if (categoryLinks != null)
            {
                foreach (XElement cat in categoryLinks.Elements())
                {
                    if (cat.Name.LocalName != "categoryLink")
                        continue;

                    string? keyword = cat.Attribute("name")?.Value;
                    string? targetId = cat.Attribute("targetId")?.Value;

                    if (!string.IsNullOrEmpty(keyword) && !unit.Keywords.Contains(keyword))
                    {
                        unit.Keywords.Add(keyword);
                    }

                    if (!string.IsNullOrEmpty(targetId) && !unit.CategoryIds.Contains(targetId))
                    {
                        unit.CategoryIds.Add(targetId);
                    }
                }
            }

            ParseWargearOptions(entry, ns, unit);

            return unit;
        }

        private void ParseProfiles(XElement entry, XNamespace ns, Unit unit)
        {
            XElement? profiles = entry.Element(ns + "profiles") ?? entry.Element(CatNs + "profiles");
            if (profiles == null)
                return;

            foreach (XElement profile in profiles.Elements())
            {
                if (profile.Name.LocalName != "profile")
                    continue;

                string? typeName = profile.Attribute("typeName")?.Value ?? string.Empty;
                string? profileName = profile.Attribute("name")?.Value;

                if (typeName.Contains("Abilities") || typeName.Contains("Ability"))
                {
                    UnitAbility ability = ParseAbility(profile, ns);
                    if (!string.IsNullOrEmpty(ability.Name) &&
                        !unit.Abilities.Any(a => a.Name == ability.Name))
                    {
                        unit.Abilities.Add(ability);
                    }
                }
                else if (typeName.Contains("Weapon") || typeName.Contains("Ranged") || typeName.Contains("Melee"))
                {
                    UnitAbility weaponAbility = new()
                    {
                        Name = profileName ?? "Weapon",
                        Description = GetProfileDescription(profile, ns)
                    };
                    if (!string.IsNullOrEmpty(weaponAbility.Description) &&
                        !unit.Abilities.Any(a => a.Name == weaponAbility.Name))
                    {
                        unit.Abilities.Add(weaponAbility);
                    }
                }
                else if (!typeName.Contains(ExclusionKeyword, StringComparison.OrdinalIgnoreCase))
                {
                    // Any profile type that doesn't contain "Faction" is treated as a stat profile
                    UnitProfile unitProfile = ParseProfile(profile, ns);
                    if (!unit.Profiles.Any(p => p.Name == unitProfile.Name))
                    {
                        unit.Profiles.Add(unitProfile);
                    }
                }
            }
        }

        private UnitProfile ParseProfile(XElement profile, XNamespace ns)
        {
            UnitProfile unitProfile = new()
            {
                Name = profile.Attribute("name")?.Value ?? "Profile",
                TypeName = profile.Attribute("typeName")?.Value ?? string.Empty
            };

            XElement? characteristics = profile.Element(ns + "characteristics") ?? profile.Element(CatNs + "characteristics");
            if (characteristics != null)
            {
                foreach (XElement ch in characteristics.Elements())
                {
                    if (ch.Name.LocalName != "characteristic")
                        continue;

                    string? name = ch.Attribute("name")?.Value;
                    string? value = ch.Value?.Trim();

                    if (!string.IsNullOrEmpty(name))
                    {
                        unitProfile.Characteristics[name] = value ?? "-";
                    }
                }
            }

            return unitProfile;
        }

        private UnitAbility ParseAbility(XElement profile, XNamespace ns)
        {
            UnitAbility ability = new()
            {
                Name = profile.Attribute("name")?.Value ?? string.Empty,
                Description = GetProfileDescription(profile, ns)
            };

            return ability;
        }

        private string GetProfileDescription(XElement profile, XNamespace ns)
        {
            XElement? characteristics = profile.Element(ns + "characteristics") ?? profile.Element(CatNs + "characteristics");
            if (characteristics != null)
            {
                XElement? descChar = characteristics.Elements()
                    .FirstOrDefault(c => c.Attribute("name")?.Value == "Description" ||
                                         c.Attribute("name")?.Value == "Effect" ||
                                         c.Attribute("name")?.Value == "Abilities");

                if (descChar != null)
                {
                    return descChar.Value?.Trim() ?? string.Empty;
                }

                List<string> parts = new();
                foreach (XElement ch in characteristics.Elements())
                {
                    if (ch.Name.LocalName != "characteristic")
                        continue;

                    string? name = ch.Attribute("name")?.Value;
                    string? value = ch.Value?.Trim();
                    if (!string.IsNullOrEmpty(name) && !string.IsNullOrEmpty(value))
                    {
                        parts.Add($"{name}: {value}");
                    }
                }
                return string.Join(", ", parts);
            }

            return string.Empty;
        }

        private void ParseWargearOptions(XElement entry, XNamespace ns, Unit unit)
        {
            HashSet<string> addedWargearIds = new();

            XElement? selectionEntryGroups = entry.Element(ns + "selectionEntryGroups")
                ?? entry.Element(CatNs + "selectionEntryGroups");

            if (selectionEntryGroups != null)
            {
                foreach (XElement group in selectionEntryGroups.Elements())
                {
                    if (group.Name.LocalName != "selectionEntryGroup")
                        continue;

                    string groupName = group.Attribute("name")?.Value ?? "Options";

                    XElement? groupEntries = group.Element(ns + "selectionEntries")
                        ?? group.Element(CatNs + "selectionEntries");

                    if (groupEntries != null)
                    {
                        foreach (XElement optionEntry in groupEntries.Elements())
                        {
                            if (optionEntry.Name.LocalName != "selectionEntry")
                                continue;

                            string? type = optionEntry.Attribute("type")?.Value;
                            string? id = optionEntry.Attribute("id")?.Value;

                            if (type == "upgrade" && !string.IsNullOrEmpty(id) && !addedWargearIds.Contains(id))
                            {
                                WargearOption option = ParseWargearOption(optionEntry, ns, groupName);
                                if (!string.IsNullOrEmpty(option.Name))
                                {
                                    unit.WargearOptions.Add(option);
                                    addedWargearIds.Add(id);
                                }
                            }
                        }
                    }

                    XElement? entryLinks = group.Element(ns + "entryLinks")
                        ?? group.Element(CatNs + "entryLinks");

                    if (entryLinks != null)
                    {
                        foreach (XElement link in entryLinks.Elements())
                        {
                            if (link.Name.LocalName != "entryLink")
                                continue;

                            string? id = link.Attribute("id")?.Value;
                            string? name = link.Attribute("name")?.Value;

                            if (!string.IsNullOrEmpty(name) && !string.IsNullOrEmpty(id) && !addedWargearIds.Contains(id))
                            {
                                WargearOption option = new()
                                {
                                    Id = id,
                                    Name = name,
                                    GroupName = groupName,
                                    PointsCost = GetDirectPointsCost(link, ns),
                                    Description = string.Empty
                                };
                                unit.WargearOptions.Add(option);
                                addedWargearIds.Add(id);
                            }
                        }
                    }
                }
            }

            XElement? selectionEntries = entry.Element(ns + "selectionEntries")
                ?? entry.Element(CatNs + "selectionEntries");

            if (selectionEntries != null)
            {
                foreach (XElement subEntry in selectionEntries.Elements())
                {
                    if (subEntry.Name.LocalName != "selectionEntry")
                        continue;

                    string? type = subEntry.Attribute("type")?.Value;
                    string? id = subEntry.Attribute("id")?.Value;

                    if (type == "upgrade" && !string.IsNullOrEmpty(id) && !addedWargearIds.Contains(id))
                    {
                        WargearOption option = ParseWargearOption(subEntry, ns, "Upgrades");
                        if (!string.IsNullOrEmpty(option.Name))
                        {
                            unit.WargearOptions.Add(option);
                            addedWargearIds.Add(id);
                        }
                    }
                }
            }
        }

        private WargearOption ParseWargearOption(XElement entry, XNamespace ns, string groupName)
        {
            WargearOption option = new()
            {
                Id = entry.Attribute("id")?.Value ?? Guid.NewGuid().ToString(),
                Name = entry.Attribute("name")?.Value ?? string.Empty,
                GroupName = groupName,
                PointsCost = GetDirectPointsCost(entry, ns),
                IsDefault = entry.Attribute("default")?.Value == "true"
            };

            XElement? profiles = entry.Element(ns + "profiles") ?? entry.Element(CatNs + "profiles");
            if (profiles != null)
            {
                foreach (XElement profile in profiles.Elements())
                {
                    if (profile.Name.LocalName != "profile")
                        continue;

                    string? typeName = profile.Attribute("typeName")?.Value;

                    if (typeName != null && (typeName.Contains("Weapon") || typeName.Contains("Ranged") || typeName.Contains("Melee")))
                    {
                        UnitProfile weaponProfile = ParseProfile(profile, ns);
                        option.Profiles.Add(weaponProfile);

                        if (string.IsNullOrEmpty(option.Description))
                        {
                            option.Description = GetProfileDescription(profile, ns);
                        }
                    }
                }
            }

            return option;
        }

        private int GetDirectPointsCost(XElement entry, XNamespace ns)
        {
            XElement? costsElement = entry.Element(ns + "costs") ?? entry.Element(CatNs + "costs");
            if (costsElement != null)
            {
                foreach (XElement costElement in costsElement.Elements())
                {
                    if (costElement.Name.LocalName != "cost")
                        continue;

                    string? costName = costElement.Attribute("name")?.Value;
                    if (costName == "pts" || costName == "Pts" || costName == "Points")
                    {
                        string? valueStr = costElement.Attribute("value")?.Value;
                        if (double.TryParse(valueStr, out double points))
                        {
                            return (int)Math.Round(points);
                        }
                    }
                }
            }
            return 0;
        }
    }
}