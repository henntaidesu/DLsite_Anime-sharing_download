using System;
using System.Net.Http;

namespace DASD.Core;

/// <summary>HttpClient 工厂：按当前代理设置创建客户端（对应 Python 各模块的 requests.Session）。</summary>
public static class Http
{
    public const string UserAgent =
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

    public static HttpClient CreateClient(TimeSpan? timeout = null)
    {
        var (enabled, proxy) = AppConfig.ReadProxy();
        var handler = new HttpClientHandler { AllowAutoRedirect = true };
        if (enabled)
        {
            handler.Proxy = proxy;
            handler.UseProxy = true;
        }
        var client = new HttpClient(handler) { Timeout = timeout ?? TimeSpan.FromSeconds(30) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd(UserAgent);
        return client;
    }
}
