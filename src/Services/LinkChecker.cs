using System;
using System.Net.Http;
using System.Threading.Tasks;
using DASD.Core;

namespace DASD.Services;

/// <summary>直连检测下载链接是否有效，不经过中转站（对应 Python 版 doun_url_test.py）。</summary>
public static class LinkChecker
{
    // 个别网盘（如 rapidgator）对失效文件返回 200 + 错误页而非 404，
    // 需要用页面中明确的死链提示语兜底（统一小写匹配）
    private static readonly string[] DeadMarkers =
    [
        "file not found",
        "404 file",
        "file was deleted",
        "file has expired",
        "file does not exist",
    ];

    public static HttpClient MakeClient() => Http.CreateClient(TimeSpan.FromSeconds(20));

    /// <summary>
    /// 判定规则：
    /// 1. HTTP 4xx/5xx 状态 → 失效（网盘对已删除/过期文件通常返回 404，katfile 返回 500）
    /// 2. 返回 200 但页面是明确的"文件不存在"错误页 → 失效（rapidgator 等不返回 404 的网盘）
    /// 3. 其余 → 有效
    /// </summary>
    public static async Task<bool> CheckUrlAsync(string url, HttpClient client)
    {
        string text;
        try
        {
            using var response = await client.GetAsync(url);
            if ((int)response.StatusCode >= 400)
                return false;
            text = await response.Content.ReadAsStringAsync();
        }
        catch (Exception e) when (e is HttpRequestException or TaskCanceledException or UriFormatException)
        {
            return false;
        }
        var lower = text.ToLowerInvariant();
        foreach (var marker in DeadMarkers)
            if (lower.Contains(marker))
                return false;
        return true;
    }
}
