using System;
using System.Collections.Generic;
using System.Windows.Forms;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;

namespace CADDedupPlugin
{
    /// <summary>
    /// Manages multi-level warnings based on similarity trends.
    /// </summary>
    public class TrendWarningManager
    {
        private readonly Editor _editor;
        private readonly NotificationManager _notificationManager;

        public TrendWarningManager(Editor editor, NotificationManager notificationManager)
        {
            _editor = editor;
            _notificationManager = notificationManager;
        }

        /// <summary>
        /// Display appropriate warning based on trend analysis.
        /// </summary>
        public void DisplayWarning(TrendAnalysis trend, List<SimilarDrawing> similarDrawings)
        {
            switch (trend.WarningLevel)
            {
                case 0:
                    // No warning needed
                    DisplayNoWarning(trend);
                    break;

                case 1:
                    // Watch level (50-70%, increasing)
                    DisplayWatchWarning(trend, similarDrawings);
                    break;

                case 2:
                    // Caution level (70-85%, increasing)
                    DisplayCautionWarning(trend, similarDrawings);
                    break;

                case 3:
                    // Warning level (85-92% or rapid increase)
                    DisplayHighWarning(trend, similarDrawings);
                    break;

                case 4:
                    // Critical level (92%+ or very rapid increase)
                    DisplayCriticalWarning(trend, similarDrawings);
                    break;
            }
        }

        private void DisplayNoWarning(TrendAnalysis trend)
        {
            _editor.WriteMessage($"\n✅ {trend.Recommendation}");
        }

        private void DisplayWatchWarning(TrendAnalysis trend, List<SimilarDrawing> similarDrawings)
        {
            var topSimilar = similarDrawings[0];

            _editor.WriteMessage($"\n💡 WATCH: Your design is {topSimilar.Similarity:P0} similar to '{topSimilar.Filename}'");
            _editor.WriteMessage($"\n   Trend: {trend.Trend} ({trend.ChangeRate:+0.00}/hour)");
            _editor.WriteMessage($"\n   {trend.Recommendation}");

            // Gentle desktop notification (no sound)
            _notificationManager.ShowNotification(
                title: "Design Similarity Watch",
                message: $"{topSimilar.Similarity:P0} similar to existing work",
                level: NotificationLevel.Info,
                playSound: false
            );
        }

        private void DisplayCautionWarning(TrendAnalysis trend, List<SimilarDrawing> similarDrawings)
        {
            var topSimilar = similarDrawings[0];

            _editor.WriteMessage($"\n⚡ CAUTION: Similarity is {topSimilar.Similarity:P0} and {trend.Trend}!");
            _editor.WriteMessage($"\n   📊 Similar to: '{topSimilar.Filename}' by {topSimilar.Uploader}");
            _editor.WriteMessage($"\n   📈 Change rate: {trend.ChangeRate:+0.00}/hour");
            _editor.WriteMessage($"\n   {trend.Recommendation}");

            // Display timeline
            DisplayTimeline(trend.Timeline);

            // Desktop notification with sound
            _notificationManager.ShowNotification(
                title: "⚡ Design Similarity Caution",
                message: $"{topSimilar.Similarity:P0} and increasing - review recommended",
                level: NotificationLevel.Warning,
                playSound: true
            );
        }

        private void DisplayHighWarning(TrendAnalysis trend, List<SimilarDrawing> similarDrawings)
        {
            var topSimilar = similarDrawings[0];

            _editor.WriteMessage($"\n⚠️⚠️ WARNING: HIGH SIMILARITY DETECTED! ⚠️⚠️");
            _editor.WriteMessage($"\n   🎯 Your design: {topSimilar.Similarity:P0} similar to existing work");
            _editor.WriteMessage($"\n   📁 Similar file: '{topSimilar.Filename}'");
            _editor.WriteMessage($"\n   👤 Created by: {topSimilar.Uploader}");
            _editor.WriteMessage($"\n   📅 Uploaded: {topSimilar.UploadTime}");
            _editor.WriteMessage($"\n   📈 Trend: {trend.Trend} ({trend.ChangeRate:+0.00}/hour)");
            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n   {trend.Recommendation}");

            // Display timeline
            DisplayTimeline(trend.Timeline);

            // Show all similar drawings
            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n   📋 All similar drawings:");
            for (int i = 0; i < Math.Min(3, similarDrawings.Count); i++)
            {
                var sim = similarDrawings[i];
                _editor.WriteMessage($"\n      {i + 1}. {sim.Filename} - {sim.Similarity:P0} by {sim.Uploader}");
            }

            // Urgent notification with sound
            _notificationManager.ShowNotification(
                title: "⚠️ HIGH SIMILARITY WARNING",
                message: $"{topSimilar.Similarity:P0} - Review immediately!",
                level: NotificationLevel.Error,
                playSound: true
            );

            // Prompt user to view
            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n   Type 'DEDUPVIEW {topSimilar.DrawingId}' to view the similar drawing.");
        }

        private void DisplayCriticalWarning(TrendAnalysis trend, List<SimilarDrawing> similarDrawings)
        {
            var topSimilar = similarDrawings[0];

            // Command line warning
            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n🚨🚨🚨 CRITICAL: STOP WORK! 🚨🚨🚨");
            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n   Your design is {topSimilar.Similarity:P0} similar to existing work!");
            _editor.WriteMessage($"\n   This is likely duplicate effort - you may be wasting time!");
            _editor.WriteMessage($"\n");

            // Calculate time wasted
            int versions = trend.Timeline.Count;
            double hoursWasted = versions * 0.5;  // Rough estimate: 30 min per version
            _editor.WriteMessage($"\n   ⏰ Estimated time spent: ~{hoursWasted:F1} hours ({versions} versions)");
            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n   📁 Existing file: '{topSimilar.Filename}'");
            _editor.WriteMessage($"\n   👤 Created by: {topSimilar.Uploader}");
            _editor.WriteMessage($"\n   📅 Uploaded: {topSimilar.UploadTime}");
            _editor.WriteMessage($"\n");

            // Display timeline
            DisplayTimeline(trend.Timeline);

            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n   {trend.Recommendation}");
            _editor.WriteMessage($"\n");

            // Critical notification
            _notificationManager.ShowNotification(
                title: "🚨 CRITICAL: STOP WORK!",
                message: $"{topSimilar.Similarity:P0} similarity - Check existing drawing!",
                level: NotificationLevel.Error,
                playSound: true
            );

            // Show modal dialog to force acknowledgment
            ShowCriticalDialog(trend, topSimilar, hoursWasted);
        }

        private void DisplayTimeline(List<TimelinePoint> timeline)
        {
            if (timeline == null || timeline.Count < 2)
                return;

            _editor.WriteMessage($"\n");
            _editor.WriteMessage($"\n   📊 Similarity Timeline:");

            int maxToShow = Math.Min(10, timeline.Count);
            int startIndex = Math.Max(0, timeline.Count - maxToShow);

            for (int i = startIndex; i < timeline.Count; i++)
            {
                var point = timeline[i];
                string bar = GetSimilarityBar(point.MaxSimilarity);
                string warning = GetWarningIndicator(point.MaxSimilarity);

                var time = DateTime.Parse(point.Time);
                _editor.WriteMessage($"\n      V{point.Version} ({time:HH:mm})  {point.MaxSimilarity:P0} {bar} {warning}");
            }
        }

        private string GetSimilarityBar(double similarity)
        {
            int blocks = (int)(similarity * 10);
            return new string('█', blocks) + new string('▁', 10 - blocks);
        }

        private string GetWarningIndicator(double similarity)
        {
            if (similarity >= 0.92) return "🚨";
            if (similarity >= 0.85) return "⚠️⚠️";
            if (similarity >= 0.70) return "⚠️";
            if (similarity >= 0.50) return "⚡";
            return "";
        }

        private void ShowCriticalDialog(TrendAnalysis trend, SimilarDrawing topSimilar, double hoursWasted)
        {
            var doc = Autodesk.AutoCAD.ApplicationServices.Core.Application.DocumentManager.MdiActiveDocument;

            // Must run on UI thread
            doc.SendStringToExecute("", false, false, false);

            System.Windows.Forms.Application.DoEvents();

            var result = MessageBox.Show(
                $"🚨 CRITICAL SIMILARITY DETECTED!\n\n" +
                $"Your design is {topSimilar.Similarity:P0} similar to:\n" +
                $"   '{topSimilar.Filename}'\n" +
                $"   Created by: {topSimilar.Uploader}\n\n" +
                $"You've spent approximately {hoursWasted:F1} hours on this design.\n\n" +
                $"Trend: {trend.Trend} ({trend.TotalChange:+P0} total change)\n\n" +
                $"Do you want to:\n" +
                $"   YES - View the existing drawing\n" +
                $"   NO  - Continue working anyway (not recommended)\n",
                "🚨 STOP: High Similarity Warning",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning,
                MessageBoxDefaultButton.Button1
            );

            if (result == DialogResult.Yes)
            {
                // Open view command
                doc.SendStringToExecute($"DEDUPVIEW {topSimilar.DrawingId} ", true, false, false);
            }
        }
    }

    #region Data Models

    public class TrendAnalysis
    {
        public string Trend { get; set; }  // "increasing", "stable", "decreasing", "new"
        public string Severity { get; set; }  // "none", "low", "medium", "high", "critical"
        public List<TimelinePoint> Timeline { get; set; }
        public double ChangeRate { get; set; }
        public double TotalChange { get; set; }
        public string Recommendation { get; set; }
        public int WarningLevel { get; set; }  // 0-4
    }

    public class TimelinePoint
    {
        public int Version { get; set; }
        public string Time { get; set; }
        public double MaxSimilarity { get; set; }
        public List<SimilarDrawingRef> SimilarTo { get; set; }
    }

    public class SimilarDrawingRef
    {
        public int DrawingId { get; set; }
        public string Filename { get; set; }
        public double Similarity { get; set; }
    }

    public class SimilarDrawing
    {
        public int DrawingId { get; set; }
        public string Filename { get; set; }
        public string Uploader { get; set; }
        public double Similarity { get; set; }
        public string UploadTime { get; set; }
    }

    public enum NotificationLevel
    {
        Info,
        Warning,
        Error
    }

    #endregion
}
