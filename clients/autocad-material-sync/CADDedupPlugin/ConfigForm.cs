// ConfigForm.cs - 配置对话框
using System;
using System.Drawing;
using System.Windows.Forms;

namespace CADDedupPlugin
{
    /// <summary>
    /// 配置对话框
    /// </summary>
    public partial class ConfigForm : Form
    {
        private readonly DedupConfig _config;
        private readonly DedupApiClient _apiClient;

        // 控件
        private TextBox txtServerUrl;
        private TextBox txtApiKey;
        private CheckBox chkAutoCheck;
        private TrackBar trackSimilarity;
        private Label lblSimilarityValue;
        private CheckBox chkAutoIndex;
        private NumericUpDown numTimeout;
        private CheckBox chkPromptOnHigh;
        private CheckBox chkShowUniqueNotification;
        private CheckBox chkPlaySound;
        private CheckBox chkCheckConnectionOnStartup;
        private TextBox txtUsername;
        private TextBox txtDepartment;
        private TextBox txtTenantId;
        private TextBox txtOrgId;
        private TextBox txtMaterialProfileId;
        private CheckBox chkMaterialDryRunDefault;
        private Button btnTest;
        private Button btnOK;
        private Button btnCancel;
        private Button btnReset;
        private Label lblStatus;

        public ConfigForm(DedupConfig config)
        {
            _config = config;
            _apiClient = new DedupApiClient(config);
            InitializeComponent();
            LoadConfig();
        }

        private void InitializeComponent()
        {
            this.Text = "CAD查重插件配置";
            this.Width = 500;
            this.Height = 650;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;

            var tabControl = new TabControl
            {
                Dock = DockStyle.Fill,
                Padding = new Point(10, 10)
            };

            // 服务器设置选项卡
            var tabServer = new TabPage("服务器设置");
            CreateServerTab(tabServer);
            tabControl.TabPages.Add(tabServer);

            // 行为设置选项卡
            var tabBehavior = new TabPage("行为设置");
            CreateBehaviorTab(tabBehavior);
            tabControl.TabPages.Add(tabBehavior);

            // 通知设置选项卡
            var tabNotification = new TabPage("通知设置");
            CreateNotificationTab(tabNotification);
            tabControl.TabPages.Add(tabNotification);

            // 用户信息选项卡
            var tabUser = new TabPage("用户信息");
            CreateUserTab(tabUser);
            tabControl.TabPages.Add(tabUser);

            this.Controls.Add(tabControl);

            // 底部按钮
            var panelButtons = new Panel
            {
                Dock = DockStyle.Bottom,
                Height = 50
            };

            lblStatus = new Label
            {
                Location = new Point(10, 15),
                Width = 200,
                AutoSize = false
            };
            panelButtons.Controls.Add(lblStatus);

            btnReset = new Button
            {
                Text = "重置默认",
                Location = new Point(220, 10),
                Width = 80
            };
            btnReset.Click += BtnReset_Click;
            panelButtons.Controls.Add(btnReset);

            btnCancel = new Button
            {
                Text = "取消",
                Location = new Point(310, 10),
                Width = 80,
                DialogResult = DialogResult.Cancel
            };
            panelButtons.Controls.Add(btnCancel);

            btnOK = new Button
            {
                Text = "确定",
                Location = new Point(400, 10),
                Width = 80
            };
            btnOK.Click += BtnOK_Click;
            panelButtons.Controls.Add(btnOK);

            this.Controls.Add(panelButtons);
            this.AcceptButton = btnOK;
            this.CancelButton = btnCancel;
        }

        /// <summary>
        /// 创建服务器设置选项卡
        /// </summary>
        private void CreateServerTab(TabPage tab)
        {
            int y = 20;

            // 服务器地址
            var lblServer = new Label
            {
                Text = "服务器地址:",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblServer);

            txtServerUrl = new TextBox
            {
                Location = new Point(130, y),
                Width = 300
            };
            tab.Controls.Add(txtServerUrl);

            y += 40;

            // API密钥
            var lblApiKey = new Label
            {
                Text = "API密钥 (可选):",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblApiKey);

            txtApiKey = new TextBox
            {
                Location = new Point(130, y),
                Width = 300,
                UseSystemPasswordChar = true
            };
            tab.Controls.Add(txtApiKey);

            y += 40;

            var lblTenant = new Label
            {
                Text = "租户 ID:",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblTenant);

            txtTenantId = new TextBox
            {
                Location = new Point(130, y),
                Width = 130
            };
            tab.Controls.Add(txtTenantId);

            var lblOrg = new Label
            {
                Text = "组织 ID:",
                Location = new Point(270, y),
                Width = 65
            };
            tab.Controls.Add(lblOrg);

            txtOrgId = new TextBox
            {
                Location = new Point(335, y),
                Width = 95
            };
            tab.Controls.Add(txtOrgId);

            y += 40;

            var lblMaterialProfile = new Label
            {
                Text = "物料 profile:",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblMaterialProfile);

            txtMaterialProfileId = new TextBox
            {
                Location = new Point(130, y),
                Width = 130
            };
            tab.Controls.Add(txtMaterialProfileId);

            chkMaterialDryRunDefault = new CheckBox
            {
                Text = "物料回写默认仅预演",
                Location = new Point(270, y),
                Width = 160
            };
            tab.Controls.Add(chkMaterialDryRunDefault);

            y += 40;

            // 超时时间
            var lblTimeout = new Label
            {
                Text = "超时时间 (秒):",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblTimeout);

            numTimeout = new NumericUpDown
            {
                Location = new Point(130, y),
                Width = 100,
                Minimum = 5,
                Maximum = 300,
                Value = 30
            };
            tab.Controls.Add(numTimeout);

            y += 40;

            // 启动时检查连接
            chkCheckConnectionOnStartup = new CheckBox
            {
                Text = "启动时检查服务器连接",
                Location = new Point(20, y),
                Width = 200
            };
            tab.Controls.Add(chkCheckConnectionOnStartup);

            y += 40;

            // 测试连接按钮
            btnTest = new Button
            {
                Text = "测试连接",
                Location = new Point(130, y),
                Width = 100
            };
            btnTest.Click += BtnTest_Click;
            tab.Controls.Add(btnTest);

            y += 50;

            // 说明文本
            var lblHelp = new Label
            {
                Text = "说明:\n" +
                      "• 服务器地址格式: http://服务器IP:端口\n" +
                      "• 例如: http://192.168.1.100:8000\n" +
                      "• 如果服务器启用了认证，需要填写API密钥\n" +
                      "• 物料同步命令调用 /api/v1/plugins/cad-material-sync/*",
                Location = new Point(20, y),
                Width = 420,
                Height = 100,
                ForeColor = System.Drawing.Color.Gray
            };
            tab.Controls.Add(lblHelp);
        }

        /// <summary>
        /// 创建行为设置选项卡
        /// </summary>
        private void CreateBehaviorTab(TabPage tab)
        {
            int y = 20;

            // 自动检查
            chkAutoCheck = new CheckBox
            {
                Text = "保存图纸时自动检查重复",
                Location = new Point(20, y),
                Width = 250,
                Checked = true
            };
            tab.Controls.Add(chkAutoCheck);

            y += 40;

            // 相似度阈值
            var lblSimilarity = new Label
            {
                Text = "相似度阈值:",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblSimilarity);

            trackSimilarity = new TrackBar
            {
                Location = new Point(130, y),
                Width = 250,
                Minimum = 50,
                Maximum = 100,
                Value = 85,
                TickFrequency = 5
            };
            trackSimilarity.ValueChanged += TrackSimilarity_ValueChanged;
            tab.Controls.Add(trackSimilarity);

            lblSimilarityValue = new Label
            {
                Text = "85%",
                Location = new Point(390, y),
                Width = 50
            };
            tab.Controls.Add(lblSimilarityValue);

            y += 50;

            // 说明
            var lblSimilarityHelp = new Label
            {
                Text = "相似度越高，检测越严格\n" +
                      "• 90%以上: 严格模式，仅检测几乎相同的图纸\n" +
                      "• 80-90%: 标准模式（推荐）\n" +
                      "• 80%以下: 宽松模式，可能产生误报",
                Location = new Point(40, y),
                Width = 400,
                Height = 80,
                ForeColor = System.Drawing.Color.Gray
            };
            tab.Controls.Add(lblSimilarityHelp);

            y += 90;

            // 自动添加到索引库
            chkAutoIndex = new CheckBox
            {
                Text = "自动将图纸添加到查重库",
                Location = new Point(20, y),
                Width = 250,
                Checked = true
            };
            tab.Controls.Add(chkAutoIndex);

            y += 40;

            // 高相似度时提示
            chkPromptOnHigh = new CheckBox
            {
                Text = "相似度>90%时提示查看对比",
                Location = new Point(20, y),
                Width = 250,
                Checked = true
            };
            tab.Controls.Add(chkPromptOnHigh);
        }

        /// <summary>
        /// 创建通知设置选项卡
        /// </summary>
        private void CreateNotificationTab(TabPage tab)
        {
            int y = 20;

            chkShowUniqueNotification = new CheckBox
            {
                Text = "未发现重复时显示通知",
                Location = new Point(20, y),
                Width = 250
            };
            tab.Controls.Add(chkShowUniqueNotification);

            y += 40;

            chkPlaySound = new CheckBox
            {
                Text = "发现重复时播放声音",
                Location = new Point(20, y),
                Width = 250,
                Checked = true
            };
            tab.Controls.Add(chkPlaySound);

            y += 50;

            var lblHelp = new Label
            {
                Text = "通知说明:\n" +
                      "• 发现重复时总是显示通知\n" +
                      "• 点击通知可查看详细对比\n" +
                      "• 通知会在10秒后自动消失",
                Location = new Point(20, y),
                Width = 400,
                Height = 70,
                ForeColor = System.Drawing.Color.Gray
            };
            tab.Controls.Add(lblHelp);
        }

        /// <summary>
        /// 创建用户信息选项卡
        /// </summary>
        private void CreateUserTab(TabPage tab)
        {
            int y = 20;

            var lblUsername = new Label
            {
                Text = "用户名:",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblUsername);

            txtUsername = new TextBox
            {
                Location = new Point(130, y),
                Width = 300
            };
            tab.Controls.Add(txtUsername);

            y += 40;

            var lblDepartment = new Label
            {
                Text = "部门:",
                Location = new Point(20, y),
                Width = 100
            };
            tab.Controls.Add(lblDepartment);

            txtDepartment = new TextBox
            {
                Location = new Point(130, y),
                Width = 300
            };
            tab.Controls.Add(txtDepartment);

            y += 50;

            var lblHelp = new Label
            {
                Text = "用户信息说明:\n" +
                      "• 用于统计和分析使用情况\n" +
                      "• 不会影响查重功能\n" +
                      "• 可留空",
                Location = new Point(20, y),
                Width = 400,
                Height = 70,
                ForeColor = System.Drawing.Color.Gray
            };
            tab.Controls.Add(lblHelp);
        }

        /// <summary>
        /// 加载配置到界面
        /// </summary>
        private void LoadConfig()
        {
            txtServerUrl.Text = _config.ServerUrl;
            txtApiKey.Text = _config.ApiKey;
            chkAutoCheck.Checked = _config.AutoCheckEnabled;
            trackSimilarity.Value = (int)(_config.SimilarityThreshold * 100);
            chkAutoIndex.Checked = _config.AutoIndex;
            numTimeout.Value = _config.TimeoutSeconds;
            chkPromptOnHigh.Checked = _config.PromptOnHighSimilarity;
            chkShowUniqueNotification.Checked = _config.ShowNotificationOnUnique;
            chkPlaySound.Checked = _config.PlaySoundOnDuplicate;
            chkCheckConnectionOnStartup.Checked = _config.CheckConnectionOnStartup;
            txtUsername.Text = _config.Username;
            txtDepartment.Text = _config.Department;
            txtTenantId.Text = _config.TenantId;
            txtOrgId.Text = _config.OrgId;
            txtMaterialProfileId.Text = _config.MaterialProfileId;
            chkMaterialDryRunDefault.Checked = _config.MaterialSyncDryRunDefault;
        }

        /// <summary>
        /// 保存界面配置
        /// </summary>
        private void SaveConfig()
        {
            _config.ServerUrl = txtServerUrl.Text.Trim();
            _config.ApiKey = txtApiKey.Text.Trim();
            _config.AutoCheckEnabled = chkAutoCheck.Checked;
            _config.SimilarityThreshold = trackSimilarity.Value / 100.0;
            _config.AutoIndex = chkAutoIndex.Checked;
            _config.TimeoutSeconds = (int)numTimeout.Value;
            _config.PromptOnHighSimilarity = chkPromptOnHigh.Checked;
            _config.ShowNotificationOnUnique = chkShowUniqueNotification.Checked;
            _config.PlaySoundOnDuplicate = chkPlaySound.Checked;
            _config.CheckConnectionOnStartup = chkCheckConnectionOnStartup.Checked;
            _config.Username = txtUsername.Text.Trim();
            _config.Department = txtDepartment.Text.Trim();
            _config.TenantId = txtTenantId.Text.Trim();
            _config.OrgId = txtOrgId.Text.Trim();
            _config.MaterialProfileId = txtMaterialProfileId.Text.Trim();
            _config.MaterialSyncDryRunDefault = chkMaterialDryRunDefault.Checked;
        }

        /// <summary>
        /// 相似度滑块值改变
        /// </summary>
        private void TrackSimilarity_ValueChanged(object sender, EventArgs e)
        {
            lblSimilarityValue.Text = $"{trackSimilarity.Value}%";
        }

        /// <summary>
        /// 测试连接按钮
        /// </summary>
        private async void BtnTest_Click(object sender, EventArgs e)
        {
            btnTest.Enabled = false;
            lblStatus.Text = "测试中...";

            try
            {
                // 临时更新配置
                var tempConfig = new DedupConfig
                {
                    ServerUrl = txtServerUrl.Text.Trim(),
                    ApiKey = txtApiKey.Text.Trim(),
                    TenantId = txtTenantId.Text.Trim(),
                    OrgId = txtOrgId.Text.Trim()
                };
                var tempClient = new DedupApiClient(tempConfig);

                bool success = await tempClient.TestConnectionAsync();

                if (success)
                {
                    lblStatus.Text = "✓ 连接成功";
                    lblStatus.ForeColor = System.Drawing.Color.Green;
                }
                else
                {
                    lblStatus.Text = "✗ 连接失败";
                    lblStatus.ForeColor = System.Drawing.Color.Red;
                }
            }
            catch (Exception ex)
            {
                lblStatus.Text = $"✗ 错误: {ex.Message}";
                lblStatus.ForeColor = System.Drawing.Color.Red;
            }
            finally
            {
                btnTest.Enabled = true;
            }
        }

        /// <summary>
        /// 重置按钮
        /// </summary>
        private void BtnReset_Click(object sender, EventArgs e)
        {
            var result = MessageBox.Show(
                "确定要重置为默认配置吗？",
                "确认",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question
            );

            if (result == DialogResult.Yes)
            {
                _config.ResetToDefault();
                LoadConfig();
                lblStatus.Text = "已重置为默认配置";
                lblStatus.ForeColor = System.Drawing.Color.Blue;
            }
        }

        /// <summary>
        /// 确定按钮
        /// </summary>
        private void BtnOK_Click(object sender, EventArgs e)
        {
            SaveConfig();

            if (!_config.Validate(out string errorMessage))
            {
                MessageBox.Show(errorMessage, "配置错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            this.DialogResult = DialogResult.OK;
            this.Close();
        }
    }
}
