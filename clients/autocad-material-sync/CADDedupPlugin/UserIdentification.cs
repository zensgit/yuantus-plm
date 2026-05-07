using System;
using System.DirectoryServices.AccountManagement;
using System.Management;
using System.Net;

namespace CADDedupPlugin
{
    /// <summary>
    /// Level 0 User Identification - No authentication, just identify the user.
    ///
    /// This class provides simple user identification without requiring login or authentication.
    /// Perfect for small teams (8-15 users) where everyone is trusted.
    /// </summary>
    public class UserIdentification
    {
        private static string _cachedUserName;
        private static string _cachedComputerName;
        private static string _cachedFullName;

        /// <summary>
        /// Get current user name (Windows login name).
        /// Example: "zhangsan" or "DOMAIN\\zhangsan"
        /// </summary>
        public static string GetUserName()
        {
            if (!string.IsNullOrEmpty(_cachedUserName))
                return _cachedUserName;

            try
            {
                // Method 1: Environment.UserName (fastest, most reliable)
                _cachedUserName = Environment.UserName;

                // Remove domain prefix if present
                if (_cachedUserName.Contains("\\"))
                {
                    _cachedUserName = _cachedUserName.Split('\\')[1];
                }

                return _cachedUserName;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error getting username: {ex.Message}");
                return "unknown_user";
            }
        }

        /// <summary>
        /// Get user's full name (display name).
        /// Example: "张三" or "Zhang San"
        /// </summary>
        public static string GetUserFullName()
        {
            if (!string.IsNullOrEmpty(_cachedFullName))
                return _cachedFullName;

            try
            {
                // Try to get full name from Active Directory or local user
                using (var user = UserPrincipal.Current)
                {
                    if (user != null && !string.IsNullOrEmpty(user.DisplayName))
                    {
                        _cachedFullName = user.DisplayName;
                        return _cachedFullName;
                    }
                }
            }
            catch
            {
                // AD lookup failed, fall back to login name
            }

            // Fallback: use login name
            _cachedFullName = GetUserName();
            return _cachedFullName;
        }

        /// <summary>
        /// Get computer name.
        /// Example: "CAD-WORKSTATION-01"
        /// </summary>
        public static string GetComputerName()
        {
            if (!string.IsNullOrEmpty(_cachedComputerName))
                return _cachedComputerName;

            try
            {
                _cachedComputerName = Environment.MachineName;
                return _cachedComputerName;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error getting computer name: {ex.Message}");
                return "unknown_computer";
            }
        }

        /// <summary>
        /// Get user identification info for display.
        /// </summary>
        public static UserInfo GetUserInfo()
        {
            return new UserInfo
            {
                UserName = GetUserName(),
                FullName = GetUserFullName(),
                ComputerName = GetComputerName(),
                IdentificationMethod = "Windows Login"
            };
        }

        /// <summary>
        /// Get user-friendly display name for UI.
        /// Prefers full name, falls back to username.
        /// </summary>
        public static string GetDisplayName()
        {
            string fullName = GetUserFullName();
            string userName = GetUserName();

            // If full name is different from username, use it
            if (fullName != userName)
            {
                return $"{fullName} ({userName})";
            }

            return userName;
        }

        /// <summary>
        /// Clear cached values (for testing or re-identification).
        /// </summary>
        public static void ClearCache()
        {
            _cachedUserName = null;
            _cachedComputerName = null;
            _cachedFullName = null;
        }

        /// <summary>
        /// Validate if current user can be identified.
        /// </summary>
        public static bool CanIdentifyUser()
        {
            try
            {
                string userName = GetUserName();
                return !string.IsNullOrEmpty(userName) && userName != "unknown_user";
            }
            catch
            {
                return false;
            }
        }
    }

    /// <summary>
    /// User identification information.
    /// </summary>
    public class UserInfo
    {
        /// <summary>Login username (e.g., "zhangsan")</summary>
        public string UserName { get; set; }

        /// <summary>Full display name (e.g., "张三")</summary>
        public string FullName { get; set; }

        /// <summary>Computer name (e.g., "CAD-WS-01")</summary>
        public string ComputerName { get; set; }

        /// <summary>How user was identified</summary>
        public string IdentificationMethod { get; set; }

        /// <summary>User-friendly display string</summary>
        public override string ToString()
        {
            if (FullName != UserName)
            {
                return $"{FullName} ({UserName}) @ {ComputerName}";
            }
            return $"{UserName} @ {ComputerName}";
        }
    }
}
