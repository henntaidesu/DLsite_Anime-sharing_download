using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using DASD.Core;

namespace DASD.Services;

/// <summary>DL suggest API 返回的作品数据（对应 Python 版 get_work_data 的 dict）。</summary>
public class DlWork
{
    public string WorkName { get; init; } = "";
    public string WorkNo { get; init; } = "";
    public string MakerName { get; init; } = "";
    public string MakerId { get; init; } = "";
    public string WorkType { get; init; } = "";
    public string IntroS { get; init; } = "";
    public string AgeCategory { get; init; } = "";
    public string IsAna { get; init; } = "";
}

/// <summary>DLsite 公开 suggest API 客户端（对应 Python 版 DLapi_call.py）。</summary>
public static class DlsiteApi
{
    /// <summary>调用 DL suggest API，返回该 RJ 号作品的全部数据；未获取到返回 null。</summary>
    public static async Task<DlWork?> GetWorkDataAsync(string workId)
    {
        try
        {
            using var client = Http.CreateClient(TimeSpan.FromSeconds(15));
            var timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            var url = $"https://www.dlsite.com/suggest/?term={workId}&site=adult-jp&time={timestamp}&touch=0&_={timestamp + 10}";
            var text = await client.GetStringAsync(url);
            using var doc = JsonDocument.Parse(text);
            if (!doc.RootElement.TryGetProperty("work", out var works) ||
                works.ValueKind != JsonValueKind.Array)
                return null;

            JsonElement? first = null;
            foreach (var work in works.EnumerateArray())
            {
                first ??= work;
                // 优先返回 workno 完全匹配的作品
                if (string.Equals(JStr(work, "workno"), workId, StringComparison.OrdinalIgnoreCase))
                    return Parse(work);
            }
            return first is { } f ? Parse(f) : null;
        }
        catch (Exception e)
        {
            Logger.Error(e, "DLsite suggest API");
            return null;
        }
    }

    /// <summary>仅取作品名称（文件夹按作品名命名时使用），失败返回 null。</summary>
    public static async Task<string?> GetWorkNameAsync(string workId)
    {
        var work = await GetWorkDataAsync(workId);
        return string.IsNullOrEmpty(work?.WorkName) ? null : work!.WorkName;
    }

    private static DlWork Parse(JsonElement work) => new()
    {
        WorkName = JStr(work, "work_name"),
        WorkNo = JStr(work, "workno"),
        MakerName = JStr(work, "maker_name"),
        MakerId = JStr(work, "maker_id"),
        WorkType = JStr(work, "work_type"),
        IntroS = JStr(work, "intro_s"),
        AgeCategory = JStr(work, "age_category"),
        IsAna = JStr(work, "is_ana"),
    };

    /// <summary>取 JSON 属性为字符串（数字/布尔等也转为字符串），缺失为空串。</summary>
    internal static string JStr(JsonElement element, string prop)
    {
        if (element.ValueKind != JsonValueKind.Object || !element.TryGetProperty(prop, out var v))
            return "";
        return v.ValueKind switch
        {
            JsonValueKind.String => v.GetString() ?? "",
            JsonValueKind.Null or JsonValueKind.Undefined => "",
            _ => v.GetRawText(),
        };
    }
}
