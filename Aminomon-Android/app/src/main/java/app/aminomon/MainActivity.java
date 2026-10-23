package app.aminomon;

import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/**
 * Hosts the offline web build of Aminomon (assets/www) in a WebView.
 *
 * The game runs Python (Pyodide) in a Web Worker that blocks on a
 * SharedArrayBuffer, which browsers only allow on "cross-origin isolated"
 * pages. WebView has no switch for that, so every request for our private
 * https origin is answered here, from the APK's assets, with the COOP/COEP
 * headers added. Nothing ever touches the network.
 */
public class MainActivity extends Activity {
    private static final String HOST = "appassets.aminomon.local";
    private static final String ORIGIN = "https://" + HOST + "/";
    private WebView web;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.parseColor("#121212")));
        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#121212"));
        setContentView(web);
        setup(web);
        web.loadUrl(ORIGIN + "index.html");
        hideSystemBars();
    }

    private void setup(final WebView w) {
        WebSettings s = w.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        w.setOverScrollMode(View.OVER_SCROLL_NEVER);
        w.setLongClickable(false);
        w.setOnLongClickListener(v -> true);
        w.addJavascriptInterface(new Object() {
            @JavascriptInterface public void quit() { runOnUiThread(MainActivity.this::finish); }
        }, "AndroidBridge");
        w.setWebChromeClient(new WebChromeClient());
        w.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                if (!r.getUrl().getHost().equals(HOST)) return blocked();   // offline game: no other hosts
                return serve(r.getUrl().getPath());
            }
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { return true; }
            @Override
            public boolean onRenderProcessGone(WebView v, RenderProcessGoneDetail d) {
                runOnUiThread(() -> recreate());       // low memory: start again, the save is in localStorage
                return true;
            }
        });
    }

    private WebResourceResponse blocked() {
        return new WebResourceResponse("text/plain", "utf-8", 403, "Blocked", new HashMap<String, String>(), new java.io.ByteArrayInputStream(new byte[0]));
    }

    private WebResourceResponse serve(String path) {
        if (path == null || path.equals("/") || path.isEmpty()) path = "/index.html";
        path = path.substring(1);
        if (path.contains("..")) return blocked();
        try {
            InputStream in = getAssets().open("www/" + path);
            Map<String, String> h = new HashMap<>();
            h.put("Cross-Origin-Opener-Policy", "same-origin");
            h.put("Cross-Origin-Embedder-Policy", "require-corp");
            h.put("Cross-Origin-Resource-Policy", "same-origin");
            h.put("Cache-Control", "no-cache");
            h.put("Access-Control-Allow-Origin", ORIGIN.substring(0, ORIGIN.length() - 1));
            String mime = mime(path);
            return new WebResourceResponse(mime, mime.startsWith("text/") || mime.contains("json") || mime.contains("javascript") ? "utf-8" : null, 200, "OK", h, in);
        } catch (IOException e) {
            return new WebResourceResponse("text/plain", "utf-8", 404, "Not found", new HashMap<String, String>(), new java.io.ByteArrayInputStream(new byte[0]));
        }
    }

    private static String mime(String p) {
        p = p.toLowerCase();
        if (p.endsWith(".html")) return "text/html";
        if (p.endsWith(".js") || p.endsWith(".mjs")) return "text/javascript";
        if (p.endsWith(".wasm")) return "application/wasm";
        if (p.endsWith(".json") || p.endsWith(".webmanifest")) return p.endsWith(".json") ? "application/json" : "application/manifest+json";
        if (p.endsWith(".zip")) return "application/zip";
        if (p.endsWith(".woff")) return "font/woff";
        if (p.endsWith(".png")) return "image/png";
        if (p.endsWith(".css")) return "text/css";
        return "application/octet-stream";
    }

    private void hideSystemBars() {
        View d = getWindow().getDecorView();
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            android.view.WindowInsetsController c = getWindow().getInsetsController();
            if (c != null) {
                c.hide(android.view.WindowInsets.Type.systemBars());
                c.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
            }
        } else {
            d.setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
    }

    @Override public void onWindowFocusChanged(boolean f) { super.onWindowFocusChanged(f); if (f) hideSystemBars(); }

    @Override
    public boolean onKeyDown(int code, KeyEvent e) {
        if (code == KeyEvent.KEYCODE_BACK) {
            // Back = Esc inside the game; if the game has closed, leave the app
            web.evaluateJavascript("window.gvBack ? window.gvBack() : 'quit'", v -> {
                if (v != null && v.contains("quit")) finish();
            });
            return true;
        }
        return super.onKeyDown(code, e);
    }

    @Override protected void onDestroy() { if (web != null) web.destroy(); super.onDestroy(); }
}
