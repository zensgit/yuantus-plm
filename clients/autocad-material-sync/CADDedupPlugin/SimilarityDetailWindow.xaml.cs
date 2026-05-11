// SimilarityDetailWindow.xaml.cs - 相似度详细分析窗口
// 版本: 1.0.0
// 功能: 显示图纸相似度详细分析结果

using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Media;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace CADDedupPlugin
{
    public partial class SimilarityDetailWindow : Window
    {
        private readonly SimilarityAnalysisData _analysisData;

        public SimilarityDetailWindow(SimilarityAnalysisData analysisData)
        {
            InitializeComponent();
            _analysisData = analysisData ?? throw new ArgumentNullException(nameof(analysisData));

            LoadAnalysisData();
        }

        /// <summary>
        /// 加载分析数据到UI
        /// </summary>
        private void LoadAnalysisData()
        {
            try
            {
                // 时间戳
                txtTimestamp.Text = $"分析时间：{DateTime.Now:yyyy-MM-dd HH:mm:ss}";

                // 总体相似度
                double similarity = _analysisData.OverallSimilarity;
                txtOverallSimilarity.Text = $"{similarity * 100:F1}%";
                txtOverallSimilarity.Foreground = GetSimilarityColor(similarity);

                // 相似度分解
                if (_analysisData.Breakdown != null)
                {
                    LoadBreakdown(_analysisData.Breakdown);
                }

                // 相似原因
                if (_analysisData.SimilarityReasons != null && _analysisData.SimilarityReasons.Count > 0)
                {
                    listReasons.ItemsSource = _analysisData.SimilarityReasons;
                }
                else
                {
                    listReasons.ItemsSource = new List<string> { "无详细相似原因数据" };
                }

                // 关键差异
                if (_analysisData.KeyDifferences != null && _analysisData.KeyDifferences.Count > 0)
                {
                    listDifferences.ItemsSource = _analysisData.KeyDifferences;
                }
                else
                {
                    listDifferences.ItemsSource = new List<string> { "无显著差异" };
                }

                // 特征对比
                if (_analysisData.FeatureComparison != null && _analysisData.FeatureComparison.Count > 0)
                {
                    gridFeatureComparison.ItemsSource = _analysisData.FeatureComparison;
                }

                // 综合评估
                if (!string.IsNullOrEmpty(_analysisData.Summary))
                {
                    txtSummary.Text = _analysisData.Summary;
                }
                else
                {
                    txtSummary.Text = GenerateDefaultSummary(similarity);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"加载分析数据时出错：{ex.Message}",
                    "错误",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error
                );
            }
        }

        /// <summary>
        /// 加载相似度分解数据
        /// </summary>
        private void LoadBreakdown(SimilarityBreakdownData breakdown)
        {
            // 形状相似度
            barShapeSimilarity.Value = breakdown.ShapeSimilarity;
            txtShapeSimilarity.Text = $"{breakdown.ShapeSimilarity * 100:F1}%";
            txtShapeSimilarity.Foreground = GetSimilarityColor(breakdown.ShapeSimilarity);

            // 特征相似度
            barFeatureSimilarity.Value = breakdown.FeatureSimilarity;
            txtFeatureSimilarity.Text = $"{breakdown.FeatureSimilarity * 100:F1}%";
            txtFeatureSimilarity.Foreground = GetSimilarityColor(breakdown.FeatureSimilarity);

            // 尺寸相似度
            barDimensionSimilarity.Value = breakdown.DimensionSimilarity;
            txtDimensionSimilarity.Text = $"{breakdown.DimensionSimilarity * 100:F1}%";
            txtDimensionSimilarity.Foreground = GetSimilarityColor(breakdown.DimensionSimilarity);
        }

        /// <summary>
        /// 根据相似度返回颜色
        /// </summary>
        private Brush GetSimilarityColor(double similarity)
        {
            if (similarity >= 0.90) return new SolidColorBrush(Color.FromRgb(76, 175, 80));   // 绿色 - 高度相似
            if (similarity >= 0.75) return new SolidColorBrush(Color.FromRgb(255, 152, 0));   // 橙色 - 较为相似
            if (similarity >= 0.60) return new SolidColorBrush(Color.FromRgb(255, 193, 7));   // 黄色 - 中等相似
            return new SolidColorBrush(Color.FromRgb(158, 158, 158));                         // 灰色 - 低相似度
        }

        /// <summary>
        /// 生成默认摘要
        /// </summary>
        private string GenerateDefaultSummary(double similarity)
        {
            string level;
            if (similarity >= 0.95) level = "极高";
            else if (similarity >= 0.85) level = "很高";
            else if (similarity >= 0.75) level = "较高";
            else if (similarity >= 0.60) level = "中等";
            else level = "较低";

            return $"图纸相似度{level}（{similarity * 100:F1}%）。建议仔细对比关键尺寸和特征细节，确认是否可以复用现有图纸。";
        }

        /// <summary>
        /// 导出报告按钮点击
        /// </summary>
        private void BtnExport_Click(object sender, RoutedEventArgs e)
        {
            try
            {
                // 生成报告文件名
                string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string filename = $"相似度分析报告_{timestamp}.txt";

                // 选择保存位置
                var dialog = new Microsoft.Win32.SaveFileDialog
                {
                    Filter = "文本文件|*.txt|所有文件|*.*",
                    FileName = filename
                };

                if (dialog.ShowDialog() == true)
                {
                    ExportReport(dialog.FileName);
                    MessageBox.Show(
                        $"报告已导出至：\n{dialog.FileName}",
                        "导出成功",
                        MessageBoxButton.OK,
                        MessageBoxImage.Information
                    );
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"导出报告时出错：{ex.Message}",
                    "导出失败",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error
                );
            }
        }

        /// <summary>
        /// 导出报告到文本文件
        /// </summary>
        private void ExportReport(string filePath)
        {
            using (var writer = new StreamWriter(filePath, false, System.Text.Encoding.UTF8))
            {
                writer.WriteLine("======================================");
                writer.WriteLine("      CAD图纸相似度分析报告");
                writer.WriteLine("======================================");
                writer.WriteLine();
                writer.WriteLine($"分析时间：{DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                writer.WriteLine($"总体相似度：{_analysisData.OverallSimilarity * 100:F1}%");
                writer.WriteLine();

                // 相似度分解
                if (_analysisData.Breakdown != null)
                {
                    writer.WriteLine("--- 相似度分解 ---");
                    writer.WriteLine($"  形状相似度：{_analysisData.Breakdown.ShapeSimilarity * 100:F1}%");
                    writer.WriteLine($"  特征相似度：{_analysisData.Breakdown.FeatureSimilarity * 100:F1}%");
                    writer.WriteLine($"  尺寸相似度：{_analysisData.Breakdown.DimensionSimilarity * 100:F1}%");
                    writer.WriteLine();
                }

                // 相似原因
                if (_analysisData.SimilarityReasons != null && _analysisData.SimilarityReasons.Count > 0)
                {
                    writer.WriteLine("--- 相似原因 ---");
                    foreach (var reason in _analysisData.SimilarityReasons)
                    {
                        writer.WriteLine($"  • {reason}");
                    }
                    writer.WriteLine();
                }

                // 关键差异
                if (_analysisData.KeyDifferences != null && _analysisData.KeyDifferences.Count > 0)
                {
                    writer.WriteLine("--- 关键差异 ---");
                    foreach (var diff in _analysisData.KeyDifferences)
                    {
                        writer.WriteLine($"  • {diff}");
                    }
                    writer.WriteLine();
                }

                // 特征对比
                if (_analysisData.FeatureComparison != null && _analysisData.FeatureComparison.Count > 0)
                {
                    writer.WriteLine("--- 特征对比 ---");
                    writer.WriteLine($"{"特征类型",-15} {"原图",-10} {"新图",-10} {"状态",-12} 详细说明");
                    writer.WriteLine(new string('-', 70));
                    foreach (var feature in _analysisData.FeatureComparison)
                    {
                        writer.WriteLine(
                            $"{feature.FeatureType,-15} {feature.OriginalCount,-10} {feature.NewCount,-10} " +
                            $"{feature.MatchStatus,-12} {feature.Details ?? ""}"
                        );
                    }
                    writer.WriteLine();
                }

                // 综合评估
                writer.WriteLine("--- 综合评估 ---");
                writer.WriteLine(_analysisData.Summary ?? GenerateDefaultSummary(_analysisData.OverallSimilarity));
                writer.WriteLine();
                writer.WriteLine("======================================");
            }
        }

        /// <summary>
        /// 关闭按钮点击
        /// </summary>
        private void BtnClose_Click(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        /// <summary>
        /// 从API响应的similarity_analysis JSON创建分析数据
        /// </summary>
        public static SimilarityAnalysisData FromApiResponse(double overallSimilarity, JObject similarityAnalysisJson)
        {
            var data = new SimilarityAnalysisData
            {
                OverallSimilarity = overallSimilarity
            };

            if (similarityAnalysisJson == null)
            {
                return data;
            }

            try
            {
                // 解析breakdown
                if (similarityAnalysisJson["breakdown"] != null)
                {
                    data.Breakdown = new SimilarityBreakdownData
                    {
                        ShapeSimilarity = similarityAnalysisJson["breakdown"]["shape_similarity"]?.Value<double>() ?? 0,
                        FeatureSimilarity = similarityAnalysisJson["breakdown"]["feature_similarity"]?.Value<double>() ?? 0,
                        DimensionSimilarity = similarityAnalysisJson["breakdown"]["dimension_similarity"]?.Value<double>() ?? 0
                    };
                }

                // 解析similarity_reasons
                if (similarityAnalysisJson["similarity_reasons"] != null)
                {
                    data.SimilarityReasons = similarityAnalysisJson["similarity_reasons"].ToObject<List<string>>();
                }

                // 解析key_differences
                if (similarityAnalysisJson["key_differences"] != null)
                {
                    data.KeyDifferences = similarityAnalysisJson["key_differences"].ToObject<List<string>>();
                }

                // 解析feature_comparison
                if (similarityAnalysisJson["feature_comparison"] != null)
                {
                    var features = new List<FeatureComparisonData>();
                    foreach (var item in similarityAnalysisJson["feature_comparison"])
                    {
                        features.Add(new FeatureComparisonData
                        {
                            FeatureType = item["feature_type"]?.Value<string>() ?? "",
                            OriginalCount = item["original_count"]?.Value<int>() ?? 0,
                            NewCount = item["new_count"]?.Value<int>() ?? 0,
                            MatchStatus = item["match_status"]?.Value<string>() ?? "",
                            Details = item["details"]?.Value<string>()
                        });
                    }
                    data.FeatureComparison = features;
                }

                // 解析summary
                data.Summary = similarityAnalysisJson["summary"]?.Value<string>();
            }
            catch (Exception ex)
            {
                // 如果解析失败，返回基本数据
                System.Diagnostics.Debug.WriteLine($"Error parsing similarity analysis: {ex.Message}");
            }

            return data;
        }
    }

    #region 数据模型

    /// <summary>
    /// 相似度分析数据
    /// </summary>
    public class SimilarityAnalysisData
    {
        public double OverallSimilarity { get; set; }
        public SimilarityBreakdownData Breakdown { get; set; }
        public List<string> SimilarityReasons { get; set; }
        public List<string> KeyDifferences { get; set; }
        public List<FeatureComparisonData> FeatureComparison { get; set; }
        public string Summary { get; set; }
    }

    /// <summary>
    /// 相似度分解数据
    /// </summary>
    public class SimilarityBreakdownData
    {
        public double ShapeSimilarity { get; set; }
        public double FeatureSimilarity { get; set; }
        public double DimensionSimilarity { get; set; }
    }

    /// <summary>
    /// 特征对比数据（用于DataGrid绑定）
    /// </summary>
    public class FeatureComparisonData
    {
        public string FeatureType { get; set; }
        public int OriginalCount { get; set; }
        public int NewCount { get; set; }
        public string MatchStatus { get; set; }
        public string Details { get; set; }
    }

    #endregion
}
