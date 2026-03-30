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

        public List<Catalog> LoadCatalogsFromFolder(string folderPath)
        {
            List<Catalog> catalogs = new();

            if (!Directory.Exists(folderPath))
                return catalogs;

            foreach (string file in Directory.GetFiles(folderPath, "*.cat"))
            {
                Catalog? catalog = ParseCatalogFile(file);
                if (catalog != null)
                    catalogs.Add(catalog);
            }

            foreach (string file in Directory.GetFiles(folderPath, "*.catz"))
            {
                Catalog? catalog = ParseCompressedCatalogFile(file);
                if (catalog != null)
                    catalogs.Add(catalog);
            }

            return catalogs;
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
                    e.Name.EndsWith(".cat", StringComparison.OrdinalIgnoreCase));

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

            IEnumerable<XElement> selectionEntries = root.Descendants(ns + "selectionEntry")
                .Concat(root.Descendants(CatNs + "selectionEntry"));

            foreach (XElement entry in selectionEntries)
            {
                string? type = entry.Attribute("type")?.Value;

                if (type == "unit" || type == "model")
                {
                    Unit unit = ParseUnit(entry, ns);
                    catalog.Units.Add(unit);
                }
            }

            return catalog;
        }

        private Unit ParseUnit(XElement entry, XNamespace ns)
        {
            Unit unit = new()
            {
                Id = entry.Attribute("id")?.Value ?? Guid.NewGuid().ToString(),
                Name = entry.Attribute("name")?.Value ?? "Unknown Unit"
            };

            XElement? costElement = entry.Descendants(ns + "cost")
                .Concat(entry.Descendants(CatNs + "cost"))
                .FirstOrDefault(c => c.Attribute("name")?.Value == "pts" ||
                                     c.Attribute("typeId")?.Value?.Contains("point") == true);

            if (costElement != null && int.TryParse(costElement.Attribute("value")?.Value, out int points))
            {
                unit.PointsCost = points;
            }

            IEnumerable<XElement> profiles = entry.Descendants(ns + "profile")
                .Concat(entry.Descendants(CatNs + "profile"));

            foreach (XElement profile in profiles)
            {
                string? profileType = profile.Attribute("typeName")?.Value;

                if (profileType == "Unit" || profileType == "Model")
                {
                    unit.Profiles.Add(ParseProfile(profile, ns));
                }
            }

            IEnumerable<XElement> categories = entry.Descendants(ns + "categoryLink")
                .Concat(entry.Descendants(CatNs + "categoryLink"));

            foreach (XElement cat in categories)
            {
                string? keyword = cat.Attribute("name")?.Value;
                if (!string.IsNullOrEmpty(keyword))
                {
                    unit.Keywords.Add(keyword);
                }
            }

            return unit;
        }

        private UnitProfile ParseProfile(XElement profile, XNamespace ns)
        {
            UnitProfile unitProfile = new()
            {
                Name = profile.Attribute("name")?.Value ?? "Profile"
            };

            IEnumerable<XElement> characteristics = profile.Descendants(ns + "characteristic")
                .Concat(profile.Descendants(CatNs + "characteristic"));

            foreach (XElement ch in characteristics)
            {
                string? name = ch.Attribute("name")?.Value;
                string? value = ch.Value;

                if (!string.IsNullOrEmpty(name))
                {
                    unitProfile.Characteristics[name] = value ?? "-";
                }
            }

            return unitProfile;
        }
    }
}