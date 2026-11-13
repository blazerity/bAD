/* Служба bADagent: заявка, архив, смена ImagePath. Окон нет. */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <winhttp.h>
#include <wincrypt.h>
#include <bcrypt.h>
#include <iphlpapi.h>
#include <wbemidl.h>
#include <objbase.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wctype.h>

#pragma comment(linker, "/SUBSYSTEM:WINDOWS")
#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")
#pragma comment(lib, "wbemuuid.lib")
#pragma comment(lib, "iphlpapi.lib")
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "user32.lib")

#define INSTALL_DIR L"C:\\Program Files\\blazerity\\bADagent"
#define LINK_EXE L"C:\\Program Files\\blazerity\\bADagent\\bADagent.exe"
#define AGENT_EXE L"C:\\Program Files\\blazerity\\bADagent\\bin\\BadAgent.exe"
#define BIN_DIR L"C:\\Program Files\\blazerity\\bADagent\\bin"
#define DATA_DIR L"C:\\ProgramData\\blazerity\\bADagent"
#define CONFIG_PATH L"C:\\ProgramData\\blazerity\\bADagent\\config.json"
#define PROOF_PATH L"C:\\ProgramData\\blazerity\\bADagent\\enrollment_proof"
#define SIGNING_PATH L"C:\\ProgramData\\blazerity\\bADagent\\signing_key"
#define UPGRADE_KEY L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Installer\\UpgradeCodes\\{BADA0001-BADA-4B01-8BAD-00BADA000001}"
#define IMAGE_PATH L"\"C:\\Program Files\\blazerity\\bADagent\\bin\\BadAgent.exe\""
#define MAGIC "BADARC1\n"
#define PBKDF2_ITERS 100000ULL

static SERVICE_STATUS_HANDLE g_status_handle;
static SERVICE_STATUS g_status;
static HANDLE g_stop;

static void report(DWORD state) {
    g_status.dwServiceType = SERVICE_WIN32_OWN_PROCESS;
    g_status.dwCurrentState = state;
    g_status.dwControlsAccepted = (state == SERVICE_RUNNING) ? SERVICE_ACCEPT_STOP | SERVICE_ACCEPT_SHUTDOWN : 0;
    g_status.dwWin32ExitCode = NO_ERROR;
    g_status.dwCheckPoint = 0;
    g_status.dwWaitHint = (state == SERVICE_STOP_PENDING) ? 3000 : 0;
    if (g_status_handle) {
        SetServiceStatus(g_status_handle, &g_status);
    }
}

static DWORD WINAPI handler(DWORD ctrl, DWORD evt, LPVOID data, LPVOID ctx) {
    (void)evt;
    (void)data;
    (void)ctx;
    if (ctrl == SERVICE_CONTROL_STOP || ctrl == SERVICE_CONTROL_SHUTDOWN) {
        report(SERVICE_STOP_PENDING);
        if (g_stop) {
            SetEvent(g_stop);
        }
    }
    return NO_ERROR;
}

static int stopped(void) {
    return g_stop && WaitForSingleObject(g_stop, 0) == WAIT_OBJECT_0;
}

static int wait_ms(DWORD ms) {
    if (!g_stop) {
        Sleep(ms);
        return 0;
    }
    return WaitForSingleObject(g_stop, ms) == WAIT_OBJECT_0;
}

static int file_exists(const wchar_t *path) {
    DWORD a = GetFileAttributesW(path);
    return a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY);
}

static void ensure_dir(const wchar_t *path) {
    CreateDirectoryW(path, NULL);
}

static char *wide_to_utf8(const wchar_t *w) {
    int n;
    char *out;
    if (!w) {
        return NULL;
    }
    n = WideCharToMultiByte(CP_UTF8, 0, w, -1, NULL, 0, NULL, NULL);
    if (n <= 0) {
        return NULL;
    }
    out = (char *)malloc((size_t)n);
    if (!out) {
        return NULL;
    }
    WideCharToMultiByte(CP_UTF8, 0, w, -1, out, n, NULL, NULL);
    return out;
}

static wchar_t *utf8_to_wide(const char *s) {
    int n;
    wchar_t *out;
    if (!s) {
        return NULL;
    }
    n = MultiByteToWideChar(CP_UTF8, 0, s, -1, NULL, 0);
    if (n <= 0) {
        return NULL;
    }
    out = (wchar_t *)malloc((size_t)n * sizeof(wchar_t));
    if (!out) {
        return NULL;
    }
    MultiByteToWideChar(CP_UTF8, 0, s, -1, out, n);
    return out;
}

static void json_escape(const char *in, char *out, size_t cch) {
    size_t j = 0;
    size_t i;
    if (!in || cch == 0) {
        return;
    }
    for (i = 0; in[i] && j + 2 < cch; i++) {
        unsigned char c = (unsigned char)in[i];
        if (c == '"' || c == '\\') {
            if (j + 3 >= cch) {
                break;
            }
            out[j++] = '\\';
            out[j++] = (char)c;
        } else if (c >= 0x20) {
            out[j++] = (char)c;
        }
    }
    out[j] = 0;
}

static int hex_nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Первая строковая величина ключа. Пароль сюда попадает только в память. */
static int json_string(const char *json, const char *key, char *out, size_t cch) {
    char pat[128];
    const char *p;
    size_t j = 0;
    if (!json || !key || !out || cch == 0) {
        return 0;
    }
    out[0] = 0;
    _snprintf_s(pat, sizeof(pat), _TRUNCATE, "\"%s\"", key);
    p = strstr(json, pat);
    if (!p) {
        return 0;
    }
    p += strlen(pat);
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') {
        p++;
    }
    if (*p != ':') {
        return 0;
    }
    p++;
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') {
        p++;
    }
    if (*p != '"') {
        return 0;
    }
    p++;
    while (*p && *p != '"' && j + 1 < cch) {
        if (*p == '\\' && p[1]) {
            p++;
            if (*p == 'u' && p[1] && p[2] && p[3] && p[4]) {
                int h0 = hex_nibble(p[1]), h1 = hex_nibble(p[2]), h2 = hex_nibble(p[3]), h3 = hex_nibble(p[4]);
                if (h0 >= 0 && h1 >= 0 && h2 >= 0 && h3 >= 0) {
                    unsigned code = (unsigned)((h0 << 12) | (h1 << 8) | (h2 << 4) | h3);
                    if (code < 0x80 && j + 1 < cch) {
                        out[j++] = (char)code;
                    }
                    p += 5;
                    continue;
                }
            }
            out[j++] = *p++;
            continue;
        }
        out[j++] = *p++;
    }
    out[j] = 0;
    return *p == '"';
}

static int starts_https(const wchar_t *url) {
    return url && _wcsnicmp(url, L"https://", 8) == 0;
}

static int read_text(const wchar_t *path, char **out) {
    HANDLE h;
    DWORD size, read = 0;
    char *buf;
    h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        return 0;
    }
    size = GetFileSize(h, NULL);
    if (size == INVALID_FILE_SIZE || size > 1024 * 1024) {
        CloseHandle(h);
        return 0;
    }
    buf = (char *)malloc((size_t)size + 1);
    if (!buf) {
        CloseHandle(h);
        return 0;
    }
    if (!ReadFile(h, buf, size, &read, NULL)) {
        free(buf);
        CloseHandle(h);
        return 0;
    }
    buf[read] = 0;
    CloseHandle(h);
    *out = buf;
    return 1;
}

static int write_text(const wchar_t *path, const char *text) {
    wchar_t tmp[MAX_PATH];
    HANDLE h;
    DWORD n, written = 0;
    _snwprintf_s(tmp, MAX_PATH, _TRUNCATE, L"%s.tmp", path);
    h = CreateFileW(tmp, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) {
        return 0;
    }
    n = (DWORD)strlen(text);
    if (!WriteFile(h, text, n, &written, NULL) || written != n) {
        CloseHandle(h);
        DeleteFileW(tmp);
        return 0;
    }
    CloseHandle(h);
    if (!MoveFileExW(tmp, path, MOVEFILE_REPLACE_EXISTING)) {
        DeleteFileW(tmp);
        return 0;
    }
    return 1;
}

static int config_server(wchar_t *out, size_t cch) {
    char *text = NULL;
    char url[1024];
    wchar_t *wide;
    out[0] = 0;
    if (!read_text(CONFIG_PATH, &text)) {
        return 0;
    }
    if (!json_string(text, "server_url", url, sizeof(url)) || !url[0]) {
        free(text);
        return 0;
    }
    free(text);
    wide = utf8_to_wide(url);
    if (!wide) {
        return 0;
    }
    wcsncpy_s(out, cch, wide, _TRUNCATE);
    free(wide);
    return out[0] != 0;
}

static void ensure_server_url(wchar_t *server, size_t cch) {
    HKEY key;
    wchar_t value[1024];
    DWORD nbytes, type;
    char *utf8;
    char esc[1200];
    char body[1400];
    server[0] = 0;
    if (config_server(server, cch)) {
        return;
    }
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"SOFTWARE\\blazerity\\bADagent\\Setup", 0, KEY_READ | KEY_SET_VALUE, &key) != ERROR_SUCCESS) {
        return;
    }
    nbytes = sizeof(value);
    value[0] = 0;
    if (RegQueryValueExW(key, L"ServerUrl", NULL, &type, (LPBYTE)value, &nbytes) != ERROR_SUCCESS || type != REG_SZ) {
        RegCloseKey(key);
        return;
    }
    RegDeleteValueW(key, L"ServerUrl");
    RegCloseKey(key);
    if (!value[0]) {
        return;
    }
    ensure_dir(L"C:\\ProgramData\\blazerity");
    ensure_dir(DATA_DIR);
    utf8 = wide_to_utf8(value);
    if (!utf8) {
        return;
    }
    json_escape(utf8, esc, sizeof(esc));
    free(utf8);
    _snprintf_s(body, sizeof(body), _TRUNCATE, "{\"server_url\":\"%s\"}\n", esc);
    if (write_text(CONFIG_PATH, body)) {
        wcsncpy_s(server, cch, value, _TRUNCATE);
    }
}

static void save_secrets(const wchar_t *server, const char *api_key, const char *bad_id, const char *signing_key) {
    char *utf8;
    char esc_url[1200], esc_key[600], esc_id[80];
    char body[2200];
    ensure_dir(DATA_DIR);
    utf8 = wide_to_utf8(server);
    json_escape(utf8 ? utf8 : "", esc_url, sizeof(esc_url));
    json_escape(api_key ? api_key : "", esc_key, sizeof(esc_key));
    free(utf8);
    if (bad_id && bad_id[0]) {
        json_escape(bad_id, esc_id, sizeof(esc_id));
        _snprintf_s(body, sizeof(body), _TRUNCATE,
            "{\"server_url\":\"%s\",\"api_key\":\"%s\",\"bad_id\":\"%s\"}\n",
            esc_url, esc_key, esc_id);
    } else {
        _snprintf_s(body, sizeof(body), _TRUNCATE,
            "{\"server_url\":\"%s\",\"api_key\":\"%s\"}\n",
            esc_url, esc_key);
    }
    write_text(CONFIG_PATH, body);
    if (signing_key && signing_key[0]) {
        write_text(SIGNING_PATH, signing_key);
    }
}

static int sha256_bytes(const BYTE *data, DWORD len, char *hex, size_t hex_cch) {
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    DWORD cb_obj = 0, hash_len = 0, written = 0;
    PUCHAR obj = NULL, dig = NULL;
    NTSTATUS st;
    DWORD i;
    st = BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0);
    if (st < 0) return 0;
    BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH, (PUCHAR)&cb_obj, sizeof(cb_obj), &written, 0);
    written = 0;
    BCryptGetProperty(alg, BCRYPT_HASH_LENGTH, (PUCHAR)&hash_len, sizeof(hash_len), &written, 0);
    if (hash_len == 0 || hash_len > 64) hash_len = 32;
    obj = (PUCHAR)HeapAlloc(GetProcessHeap(), 0, cb_obj ? cb_obj : 1);
    dig = (PUCHAR)HeapAlloc(GetProcessHeap(), 0, hash_len);
    if (!obj || !dig || !cb_obj) {
        HeapFree(GetProcessHeap(), 0, obj);
        HeapFree(GetProcessHeap(), 0, dig);
        BCryptCloseAlgorithmProvider(alg, 0);
        return 0;
    }
    st = BCryptCreateHash(alg, &hash, obj, cb_obj, NULL, 0, 0);
    if (st >= 0) st = BCryptHashData(hash, (PUCHAR)data, len, 0);
    if (st >= 0) st = BCryptFinishHash(hash, dig, hash_len, 0);
    if (hash) BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);
    if (st < 0) {
        HeapFree(GetProcessHeap(), 0, obj);
        HeapFree(GetProcessHeap(), 0, dig);
        return 0;
    }
    for (i = 0; i < hash_len && (i * 2 + 2) < hex_cch; i++) {
        sprintf_s(hex + i * 2, hex_cch - i * 2, "%02x", dig[i]);
    }
    HeapFree(GetProcessHeap(), 0, obj);
    HeapFree(GetProcessHeap(), 0, dig);
    return 1;
}

static int sha256_file(const wchar_t *path, char *hex, size_t hex_cch) {
    HANDLE h;
    DWORD size, read = 0;
    BYTE *buf;
    int ok;
    h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return 0;
    size = GetFileSize(h, NULL);
    if (size == INVALID_FILE_SIZE || size > 200 * 1024 * 1024) {
        CloseHandle(h);
        return 0;
    }
    buf = (BYTE *)malloc(size ? size : 1);
    if (!buf) {
        CloseHandle(h);
        return 0;
    }
    if (!ReadFile(h, buf, size, &read, NULL)) {
        free(buf);
        CloseHandle(h);
        return 0;
    }
    CloseHandle(h);
    ok = sha256_bytes(buf, read, hex, hex_cch);
    free(buf);
    return ok;
}

static int fingerprint_hex(char *hex, size_t hex_cch) {
    HANDLE h;
    BYTE rnd[32];
    DWORD read = 0;
    BYTE *buf = NULL;
    DWORD size;
    int ok = 0;
    ensure_dir(DATA_DIR);
    if (!file_exists(PROOF_PATH)) {
        if (BCryptGenRandom(NULL, rnd, sizeof(rnd), BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) {
            return 0;
        }
        h = CreateFileW(PROOF_PATH, GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
        if (h == INVALID_HANDLE_VALUE) {
            if (GetLastError() != ERROR_FILE_EXISTS) {
                return 0;
            }
        } else {
            WriteFile(h, rnd, sizeof(rnd), &read, NULL);
            CloseHandle(h);
        }
    }
    h = CreateFileW(PROOF_PATH, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return 0;
    size = GetFileSize(h, NULL);
    if (size == 0 || size > 1024 * 1024) {
        CloseHandle(h);
        return 0;
    }
    buf = (BYTE *)malloc(size);
    if (!buf) {
        CloseHandle(h);
        return 0;
    }
    if (ReadFile(h, buf, size, &read, NULL) && read == size) {
        ok = sha256_bytes(buf, size, hex, hex_cch);
    }
    free(buf);
    CloseHandle(h);
    return ok;
}

static int all_same(const char *s, char ch) {
    if (!s || !s[0]) return 0;
    while (*s) {
        if (*s != ch) return 0;
        s++;
    }
    return 1;
}

static void trim_copy(const wchar_t *in, wchar_t *out, size_t cch) {
    const wchar_t *a = in ? in : L"";
    size_t n;
    while (*a == L' ' || *a == L'\t' || *a == L'\r' || *a == L'\n') a++;
    wcsncpy_s(out, cch, a, _TRUNCATE);
    n = wcslen(out);
    while (n && (out[n - 1] == L' ' || out[n - 1] == L'\t' || out[n - 1] == L'\r' || out[n - 1] == L'\n')) {
        out[--n] = 0;
    }
}

static int is_placeholder(const wchar_t *text) {
    wchar_t lower[256];
    size_t i;
    if (!text || !text[0]) return 1;
    for (i = 0; text[i] && i + 1 < 256; i++) {
        lower[i] = (wchar_t)towlower(text[i]);
    }
    lower[i] = 0;
    if (!wcscmp(lower, L"none") || !wcscmp(lower, L"n/a") || !wcscmp(lower, L"na")
        || !wcscmp(lower, L"default string") || !wcscmp(lower, L"system serial number")
        || !wcscmp(lower, L"system product name") || !wcscmp(lower, L"system manufacturer")
        || !wcscmp(lower, L"to be filled by o.e.m.") || !wcscmp(lower, L"o.e.m.")
        || !wcscmp(lower, L"oem") || !wcscmp(lower, L"unknown")
        || !wcscmp(lower, L"not specified") || !wcscmp(lower, L"not available")) {
        return 1;
    }
    if (wcsncmp(lower, L"to be filled", 12) == 0 || wcsncmp(lower, L"fill by oem", 11) == 0) {
        return 1;
    }
    return 0;
}

static int clean_serial(const wchar_t *raw, char *out, size_t cch) {
    wchar_t text[256];
    char *utf8;
    char compact[256];
    size_t i, j = 0;
    trim_copy(raw, text, 256);
    if (!text[0] || is_placeholder(text) || !wcscmp(text, L"0")) {
        return 0;
    }
    utf8 = wide_to_utf8(text);
    if (!utf8) return 0;
    for (i = 0; utf8[i] && j + 1 < sizeof(compact); i++) {
        char c = utf8[i];
        if (c == '-' || c == ' ' || c == '_' || c == '.') continue;
        compact[j++] = c;
    }
    compact[j] = 0;
    if (!compact[0] || all_same(compact, '0') || all_same(compact, 'F') || all_same(compact, 'f')) {
        free(utf8);
        return 0;
    }
    strncpy_s(out, cch, utf8, _TRUNCATE);
    free(utf8);
    return 1;
}

static int clean_uuid(const wchar_t *raw, char *out, size_t cch) {
    wchar_t text[128];
    char *utf8;
    char compact[128];
    size_t i, j = 0;
    trim_copy(raw, text, 128);
    if (!text[0]) return 0;
    utf8 = wide_to_utf8(text);
    if (!utf8) return 0;
    if (!_stricmp(utf8, "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF")
        || !_stricmp(utf8, "00000000-0000-0000-0000-000000000000")) {
        free(utf8);
        return 0;
    }
    for (i = 0; utf8[i] && j + 1 < sizeof(compact); i++) {
        if (utf8[i] == '-') continue;
        compact[j++] = utf8[i];
    }
    compact[j] = 0;
    if (compact[0] && (all_same(compact, 'F') || all_same(compact, 'f') || all_same(compact, '0'))) {
        free(utf8);
        return 0;
    }
    strncpy_s(out, cch, utf8, _TRUNCATE);
    free(utf8);
    return 1;
}

static int wmi_first(const wchar_t *query, const wchar_t *prop, wchar_t *out, size_t cch) {
    HRESULT hr;
    IWbemLocator *loc = NULL;
    IWbemServices *svc = NULL;
    IEnumWbemClassObject *en = NULL;
    IWbemClassObject *obj = NULL;
    VARIANT v;
    BSTR b_ns = NULL, b_wql = NULL, b_q = NULL, b_prop = NULL;
    ULONG got = 0;
    int ok = 0;
    out[0] = 0;
    hr = CoInitializeEx(NULL, COINIT_MULTITHREADED);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE) {
        return 0;
    }
    CoInitializeSecurity(NULL, -1, NULL, NULL, RPC_C_AUTHN_LEVEL_DEFAULT, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE, NULL);
    hr = CoCreateInstance(&CLSID_WbemLocator, NULL, CLSCTX_INPROC_SERVER, &IID_IWbemLocator, (void **)&loc);
    if (FAILED(hr) || !loc) return 0;
    b_ns = SysAllocString(L"ROOT\\CIMV2");
    hr = loc->lpVtbl->ConnectServer(loc, b_ns, NULL, NULL, NULL, 0, NULL, NULL, &svc);
    SysFreeString(b_ns);
    if (FAILED(hr) || !svc) {
        loc->lpVtbl->Release(loc);
        return 0;
    }
    CoSetProxyBlanket((IUnknown *)svc, RPC_C_AUTHN_WINNT, RPC_C_AUTHZ_NONE, NULL,
        RPC_C_AUTHN_LEVEL_CALL, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE);
    b_wql = SysAllocString(L"WQL");
    b_q = SysAllocString(query);
    hr = svc->lpVtbl->ExecQuery(svc, b_wql, b_q, WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY, NULL, &en);
    SysFreeString(b_wql);
    SysFreeString(b_q);
    if (FAILED(hr) || !en) {
        svc->lpVtbl->Release(svc);
        loc->lpVtbl->Release(loc);
        return 0;
    }
    hr = en->lpVtbl->Next(en, 8000, 1, &obj, &got);
    if (hr == S_OK && got && obj) {
        VariantInit(&v);
        b_prop = SysAllocString(prop);
        if (SUCCEEDED(obj->lpVtbl->Get(obj, b_prop, 0, &v, NULL, NULL)) && v.vt == VT_BSTR && v.bstrVal) {
            wcsncpy_s(out, cch, v.bstrVal, _TRUNCATE);
            ok = out[0] != 0;
        }
        SysFreeString(b_prop);
        VariantClear(&v);
        obj->lpVtbl->Release(obj);
    }
    en->lpVtbl->Release(en);
    svc->lpVtbl->Release(svc);
    loc->lpVtbl->Release(loc);
    return ok;
}

static void read_hostname(char *out, size_t cch) {
    wchar_t name[256];
    DWORD n = 256;
    char *u;
    out[0] = 0;
    if (!GetComputerNameW(name, &n)) return;
    u = wide_to_utf8(name);
    if (!u) return;
    strncpy_s(out, cch, u, _TRUNCATE);
    free(u);
}

static void read_ip(char *out, size_t cch) {
    ULONG sz = 16 * 1024;
    IP_ADAPTER_ADDRESSES *addrs = NULL, *a;
    ULONG rc;
    out[0] = 0;
    addrs = (IP_ADAPTER_ADDRESSES *)malloc(sz);
    if (!addrs) return;
    rc = GetAdaptersAddresses(AF_INET, GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST | GAA_FLAG_SKIP_DNS_SERVER, NULL, addrs, &sz);
    if (rc == ERROR_BUFFER_OVERFLOW) {
        free(addrs);
        addrs = (IP_ADAPTER_ADDRESSES *)malloc(sz);
        if (!addrs) return;
        rc = GetAdaptersAddresses(AF_INET, GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST | GAA_FLAG_SKIP_DNS_SERVER, NULL, addrs, &sz);
    }
    if (rc != NO_ERROR) {
        free(addrs);
        return;
    }
    for (a = addrs; a && !out[0]; a = a->Next) {
        IP_ADAPTER_UNICAST_ADDRESS *u;
        if (a->OperStatus != IfOperStatusUp) continue;
        if (a->IfType == IF_TYPE_SOFTWARE_LOOPBACK || a->IfType == IF_TYPE_TUNNEL) continue;
        for (u = a->FirstUnicastAddress; u; u = u->Next) {
            SOCKADDR_IN *in;
            if (!u->Address.lpSockaddr || u->Address.lpSockaddr->sa_family != AF_INET) continue;
            in = (SOCKADDR_IN *)u->Address.lpSockaddr;
            if (in->sin_addr.S_un.S_un_b.s_b1 == 127) continue;
            sprintf_s(out, cch, "%u.%u.%u.%u",
                in->sin_addr.S_un.S_un_b.s_b1,
                in->sin_addr.S_un.S_un_b.s_b2,
                in->sin_addr.S_un.S_un_b.s_b3,
                in->sin_addr.S_un.S_un_b.s_b4);
            break;
        }
    }
    free(addrs);
}

static void read_serial(char *out, size_t cch) {
    wchar_t raw[256];
    out[0] = 0;
    if (wmi_first(L"SELECT SerialNumber FROM Win32_BIOS", L"SerialNumber", raw, 256) && clean_serial(raw, out, cch)) {
        return;
    }
    out[0] = 0;
    if (wmi_first(L"SELECT IdentifyingNumber FROM Win32_ComputerSystemProduct", L"IdentifyingNumber", raw, 256)) {
        clean_serial(raw, out, cch);
    }
}

static int read_smbios(char *out, size_t cch) {
    wchar_t raw[128];
    out[0] = 0;
    if (!wmi_first(L"SELECT UUID FROM Win32_ComputerSystemProduct", L"UUID", raw, 128)) {
        return 0;
    }
    return clean_uuid(raw, out, cch);
}

static void read_machine_guid(char *out, size_t cch) {
    HKEY key;
    wchar_t value[128];
    DWORD n, type;
    char *u;
    out[0] = 0;
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, L"SOFTWARE\\Microsoft\\Cryptography", 0, KEY_READ | KEY_WOW64_64KEY, &key) != ERROR_SUCCESS) {
        return;
    }
    n = sizeof(value);
    if (RegQueryValueExW(key, L"MachineGuid", NULL, &type, (LPBYTE)value, &n) == ERROR_SUCCESS && type == REG_SZ) {
        wchar_t trimmed[128];
        trim_copy(value, trimmed, 128);
        u = wide_to_utf8(trimmed);
        if (u) {
            strncpy_s(out, cch, u, _TRUNCATE);
            free(u);
        }
    }
    RegCloseKey(key);
}

static int http_call(const wchar_t *url, const wchar_t *method, const char *bearer, const char *body, char **resp) {
    URL_COMPONENTS uc;
    wchar_t host[256], path[2048], extra[2048];
    HINTERNET ses = NULL, con = NULL, req = NULL;
    BOOL ok;
    DWORD code = 0, n = sizeof(code);
    DWORD read = 0;
    size_t cap = 8192, len = 0;
    char *buf;
    wchar_t headers[700];
    int https;
    *resp = NULL;
    ZeroMemory(&uc, sizeof(uc));
    uc.dwStructSize = sizeof(uc);
    uc.lpszHostName = host;
    uc.dwHostNameLength = 256;
    uc.lpszUrlPath = path;
    uc.dwUrlPathLength = 2048;
    uc.lpszExtraInfo = extra;
    uc.dwExtraInfoLength = 2048;
    if (!WinHttpCrackUrl(url, 0, 0, &uc)) return 0;
    https = uc.nScheme == INTERNET_SCHEME_HTTPS;
    if (!https) return 0;
    ses = WinHttpOpen(L"bADagent", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!ses) return 0;
    WinHttpSetTimeouts(ses, 10000, 15000, 20000, 60000);
    con = WinHttpConnect(ses, host, uc.nPort, 0);
    if (!con) {
        WinHttpCloseHandle(ses);
        return 0;
    }
    if (extra[0]) {
        wcsncat_s(path, 2048, extra, _TRUNCATE);
    }
    req = WinHttpOpenRequest(con, method, path, NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
    if (!req) {
        WinHttpCloseHandle(con);
        WinHttpCloseHandle(ses);
        return 0;
    }
    headers[0] = 0;
    if (body) {
        wcscpy_s(headers, 700, L"Content-Type: application/json\r\n");
    }
    if (bearer && bearer[0]) {
        wchar_t *bw = utf8_to_wide(bearer);
        if (bw) {
            wcscat_s(headers, 700, L"Authorization: Bearer ");
            wcsncat_s(headers, 700, bw, _TRUNCATE);
            wcscat_s(headers, 700, L"\r\n");
            free(bw);
        }
    }
    ok = WinHttpSendRequest(req, headers[0] ? headers : WINHTTP_NO_ADDITIONAL_HEADERS, headers[0] ? (DWORD)-1 : 0,
        body ? (LPVOID)body : WINHTTP_NO_REQUEST_DATA, body ? (DWORD)strlen(body) : 0,
        body ? (DWORD)strlen(body) : 0, 0);
    if (!ok || !WinHttpReceiveResponse(req, NULL)) {
        WinHttpCloseHandle(req);
        WinHttpCloseHandle(con);
        WinHttpCloseHandle(ses);
        return 0;
    }
    WinHttpQueryHeaders(req, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, WINHTTP_HEADER_NAME_BY_INDEX, &code, &n, WINHTTP_NO_HEADER_INDEX);
    buf = (char *)malloc(cap);
    if (!buf) {
        WinHttpCloseHandle(req);
        WinHttpCloseHandle(con);
        WinHttpCloseHandle(ses);
        return 0;
    }
    for (;;) {
        char tmp[4096];
        DWORD got = 0;
        if (!WinHttpReadData(req, tmp, sizeof(tmp), &got)) break;
        if (got == 0) break;
        if (len + got + 1 > cap) {
            char *nbuf;
            cap = (len + got + 1) * 2;
            if (cap > 4 * 1024 * 1024) break;
            nbuf = (char *)realloc(buf, cap);
            if (!nbuf) break;
            buf = nbuf;
        }
        memcpy(buf + len, tmp, got);
        len += got;
    }
    buf[len] = 0;
    WinHttpCloseHandle(req);
    WinHttpCloseHandle(con);
    WinHttpCloseHandle(ses);
    if (code < 200 || code >= 300) {
        free(buf);
        return 0;
    }
    *resp = buf;
    (void)read;
    return 1;
}

static void join_url(const wchar_t *base, const char *path_or_url, wchar_t *out, size_t cch) {
    wchar_t *w;
    size_t n;
    if (path_or_url && (strncmp(path_or_url, "https://", 8) == 0 || strncmp(path_or_url, "http://", 7) == 0)) {
        w = utf8_to_wide(path_or_url);
        if (w) {
            wcsncpy_s(out, cch, w, _TRUNCATE);
            free(w);
            return;
        }
    }
    wcsncpy_s(out, cch, base, _TRUNCATE);
    n = wcslen(out);
    while (n && out[n - 1] == L'/') {
        out[--n] = 0;
    }
    if (path_or_url && path_or_url[0] != '/') {
        wcsncat_s(out, cch, L"/", _TRUNCATE);
    }
    w = utf8_to_wide(path_or_url ? path_or_url : "");
    if (w) {
        wcsncat_s(out, cch, w, _TRUNCATE);
        free(w);
    }
}

static int download_file(const wchar_t *url, const char *bearer, const wchar_t *dest) {
    char *resp = NULL;
    /* http_call buffers the body; archives fit in the 4MB cap only if small.
       Read via a dedicated download into the file. */
    URL_COMPONENTS uc;
    wchar_t host[256], path[2048], extra[2048];
    HINTERNET ses, con, req;
    BOOL ok;
    DWORD code = 0, n = sizeof(code);
    HANDLE file;
    wchar_t headers[700];
    (void)resp;
    ZeroMemory(&uc, sizeof(uc));
    uc.dwStructSize = sizeof(uc);
    uc.lpszHostName = host;
    uc.dwHostNameLength = 256;
    uc.lpszUrlPath = path;
    uc.dwUrlPathLength = 2048;
    uc.lpszExtraInfo = extra;
    uc.dwExtraInfoLength = 2048;
    if (!WinHttpCrackUrl(url, 0, 0, &uc) || uc.nScheme != INTERNET_SCHEME_HTTPS) return 0;
    ses = WinHttpOpen(L"bADagent", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY, WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!ses) return 0;
    WinHttpSetTimeouts(ses, 10000, 20000, 60000, 120000);
    con = WinHttpConnect(ses, host, uc.nPort, 0);
    if (!con) {
        WinHttpCloseHandle(ses);
        return 0;
    }
    if (extra[0]) wcsncat_s(path, 2048, extra, _TRUNCATE);
    req = WinHttpOpenRequest(con, L"GET", path, NULL, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
    if (!req) {
        WinHttpCloseHandle(con);
        WinHttpCloseHandle(ses);
        return 0;
    }
    headers[0] = 0;
    if (bearer && bearer[0]) {
        wchar_t *bw = utf8_to_wide(bearer);
        if (bw) {
            wcscpy_s(headers, 700, L"Authorization: Bearer ");
            wcsncat_s(headers, 700, bw, _TRUNCATE);
            free(bw);
        }
    }
    ok = WinHttpSendRequest(req, headers[0] ? headers : WINHTTP_NO_ADDITIONAL_HEADERS, headers[0] ? (DWORD)-1 : 0,
        WINHTTP_NO_REQUEST_DATA, 0, 0, 0);
    if (!ok || !WinHttpReceiveResponse(req, NULL)) {
        WinHttpCloseHandle(req);
        WinHttpCloseHandle(con);
        WinHttpCloseHandle(ses);
        return 0;
    }
    WinHttpQueryHeaders(req, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER, WINHTTP_HEADER_NAME_BY_INDEX, &code, &n, WINHTTP_NO_HEADER_INDEX);
    if (code < 200 || code >= 300) {
        WinHttpCloseHandle(req);
        WinHttpCloseHandle(con);
        WinHttpCloseHandle(ses);
        return 0;
    }
    file = CreateFileW(dest, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) {
        WinHttpCloseHandle(req);
        WinHttpCloseHandle(con);
        WinHttpCloseHandle(ses);
        return 0;
    }
    for (;;) {
        BYTE tmp[16384];
        DWORD got = 0, wr = 0;
        if (!WinHttpReadData(req, tmp, sizeof(tmp), &got)) {
            CloseHandle(file);
            DeleteFileW(dest);
            WinHttpCloseHandle(req);
            WinHttpCloseHandle(con);
            WinHttpCloseHandle(ses);
            return 0;
        }
        if (got == 0) break;
        if (!WriteFile(file, tmp, got, &wr, NULL) || wr != got) {
            CloseHandle(file);
            DeleteFileW(dest);
            WinHttpCloseHandle(req);
            WinHttpCloseHandle(con);
            WinHttpCloseHandle(ses);
            return 0;
        }
    }
    CloseHandle(file);
    WinHttpCloseHandle(req);
    WinHttpCloseHandle(con);
    WinHttpCloseHandle(ses);
    return 1;
}

static int hex_eq(const char *a, const char *b) {
    return a && b && _stricmp(a, b) == 0;
}

static int decrypt_arc(const wchar_t *arc_path, const char *password, const wchar_t *zip_path) {
    HANDLE h;
    DWORD size, read = 0;
    BYTE *buf, *plain = NULL;
    BYTE key[32];
    BCRYPT_ALG_HANDLE prf = NULL, aes = NULL;
    BCRYPT_KEY_HANDLE hkey = NULL;
    BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO auth;
    NTSTATUS st;
    DWORD cb_obj = 0, cb = 0, out_len = 0;
    PUCHAR obj = NULL;
    HANDLE out;
    int ok = 0;
    const BYTE *salt, *nonce, *ct;
    BYTE *tagbuf;
    ULONG ct_len;
    h = CreateFileW(arc_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return 0;
    size = GetFileSize(h, NULL);
    if (size < 8 + 16 + 12 + 16 || size > 200 * 1024 * 1024) {
        CloseHandle(h);
        return 0;
    }
    buf = (BYTE *)malloc(size);
    if (!buf || !ReadFile(h, buf, size, &read, NULL) || read != size) {
        free(buf);
        CloseHandle(h);
        return 0;
    }
    CloseHandle(h);
    if (memcmp(buf, MAGIC, 8) != 0) {
        free(buf);
        return 0;
    }
    salt = buf + 8;
    nonce = buf + 24;
    ct = buf + 36;
    ct_len = size - 36;
    if (ct_len < 16) {
        free(buf);
        return 0;
    }
    tagbuf = (BYTE *)(ct + ct_len - 16);
    st = BCryptOpenAlgorithmProvider(&prf, BCRYPT_SHA256_ALGORITHM, NULL, BCRYPT_ALG_HANDLE_HMAC_FLAG);
    if (st < 0) {
        free(buf);
        return 0;
    }
    st = BCryptDeriveKeyPBKDF2(prf, (PUCHAR)password, (ULONG)strlen(password), (PUCHAR)salt, 16, PBKDF2_ITERS, key, 32, 0);
    BCryptCloseAlgorithmProvider(prf, 0);
    if (st < 0) {
        SecureZeroMemory(key, sizeof(key));
        free(buf);
        return 0;
    }
    st = BCryptOpenAlgorithmProvider(&aes, BCRYPT_AES_ALGORITHM, NULL, 0);
    if (st < 0) {
        SecureZeroMemory(key, sizeof(key));
        free(buf);
        return 0;
    }
    BCryptSetProperty(aes, BCRYPT_CHAINING_MODE, (PUCHAR)BCRYPT_CHAIN_MODE_GCM, (ULONG)sizeof(BCRYPT_CHAIN_MODE_GCM), 0);
    BCryptGetProperty(aes, BCRYPT_OBJECT_LENGTH, (PUCHAR)&cb_obj, sizeof(cb_obj), &cb, 0);
    obj = (PUCHAR)HeapAlloc(GetProcessHeap(), 0, cb_obj);
    st = BCryptGenerateSymmetricKey(aes, &hkey, obj, cb_obj, key, 32, 0);
    SecureZeroMemory(key, sizeof(key));
    if (st < 0) {
        HeapFree(GetProcessHeap(), 0, obj);
        BCryptCloseAlgorithmProvider(aes, 0);
        free(buf);
        return 0;
    }
    BCRYPT_INIT_AUTH_MODE_INFO(auth);
    auth.pbNonce = (PUCHAR)nonce;
    auth.cbNonce = 12;
    auth.pbTag = tagbuf;
    auth.cbTag = 16;
    plain = (BYTE *)malloc(ct_len - 16);
    if (!plain) {
        BCryptDestroyKey(hkey);
        HeapFree(GetProcessHeap(), 0, obj);
        BCryptCloseAlgorithmProvider(aes, 0);
        free(buf);
        return 0;
    }
    st = BCryptDecrypt(hkey, (PUCHAR)ct, ct_len - 16, &auth, NULL, 0, plain, ct_len - 16, &out_len, 0);
    BCryptDestroyKey(hkey);
    HeapFree(GetProcessHeap(), 0, obj);
    BCryptCloseAlgorithmProvider(aes, 0);
    free(buf);
    if (st < 0) {
        free(plain);
        return 0;
    }
    out = CreateFileW(zip_path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (out != INVALID_HANDLE_VALUE) {
        DWORD wr = 0;
        if (WriteFile(out, plain, out_len, &wr, NULL) && wr == out_len) ok = 1;
        CloseHandle(out);
        if (!ok) DeleteFileW(zip_path);
    }
    SecureZeroMemory(plain, out_len);
    free(plain);
    return ok;
}

static int zip_paths_safe(const wchar_t *zip_path) {
    HANDLE h;
    DWORD size, read = 0;
    BYTE *buf;
    DWORD i;
    int ok = 1;
    h = CreateFileW(zip_path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return 0;
    size = GetFileSize(h, NULL);
    if (size < 22 || size > 200 * 1024 * 1024) {
        CloseHandle(h);
        return 0;
    }
    buf = (BYTE *)malloc(size);
    if (!buf || !ReadFile(h, buf, size, &read, NULL) || read != size) {
        free(buf);
        CloseHandle(h);
        return 0;
    }
    CloseHandle(h);
    for (i = size - 22; ; i--) {
        if (buf[i] == 0x50 && buf[i + 1] == 0x4b && buf[i + 2] == 0x05 && buf[i + 3] == 0x06) {
            DWORD cd_off = *(DWORD *)(buf + i + 16);
            DWORD p = cd_off;
            if (cd_off >= size) {
                ok = 0;
                break;
            }
            while (p + 46 < size && buf[p] == 0x50 && buf[p + 1] == 0x4b && buf[p + 2] == 0x01 && buf[p + 3] == 0x02) {
                unsigned namelen = *(unsigned short *)(buf + p + 28);
                unsigned extra = *(unsigned short *)(buf + p + 30);
                unsigned comment = *(unsigned short *)(buf + p + 32);
                char name[1024];
                unsigned k;
                if (p + 46 + namelen > size || namelen >= sizeof(name)) {
                    ok = 0;
                    break;
                }
                memcpy(name, buf + p + 46, namelen);
                name[namelen] = 0;
                for (k = 0; name[k]; k++) {
                    if (name[k] == '\\') name[k] = '/';
                }
                if (name[0] == '/' || strchr(name, ':') || strstr(name, "../") || strcmp(name, "..") == 0
                    || (namelen >= 3 && strcmp(name + namelen - 3, "/..") == 0)) {
                    ok = 0;
                    break;
                }
                p += 46 + namelen + extra + comment;
            }
            break;
        }
        if (i == 0 || size - i > 65557) {
            ok = 0;
            break;
        }
    }
    free(buf);
    return ok;
}

static int run_hidden(wchar_t *cmdline) {
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD code = 1;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));
    if (!CreateProcessW(NULL, cmdline, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        return 0;
    }
    WaitForSingleObject(pi.hProcess, 120000);
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return code == 0;
}

static int unzip_to_bin(const wchar_t *zip_path) {
    wchar_t sys[MAX_PATH];
    wchar_t cmd[1200];
    if (!zip_paths_safe(zip_path)) return 0;
    ensure_dir(INSTALL_DIR);
    ensure_dir(BIN_DIR);
    if (!GetSystemDirectoryW(sys, MAX_PATH)) return 0;
    _snwprintf_s(cmd, 1200, _TRUNCATE, L"\"%s\\tar.exe\" -xf \"%s\" -C \"%s\"", sys, zip_path, BIN_DIR);
    return run_hidden(cmd) && file_exists(AGENT_EXE);
}

static void core_version(const char *in, char *out, size_t cch) {
    char tmp[64];
    size_t i = 0, dots = 0;
    out[0] = 0;
    if (!in) return;
    while (in[i] && in[i] != '-' && in[i] != '+' && i + 1 < sizeof(tmp)) {
        tmp[i] = in[i];
        i++;
    }
    tmp[i] = 0;
    i = 0;
    while (tmp[i] && dots < 2) {
        if (tmp[i] == '.') dots++;
        i++;
    }
    if (dots == 2) {
        while (tmp[i] && tmp[i] != '.') i++;
        tmp[i] = 0;
    }
    strncpy_s(out, cch, tmp, _TRUNCATE);
}

/* Тот же разбор, что AgentUninstaller.DecompressMsiProductCode: 25 знаков. */
static int decompress_product_code(const wchar_t *compressed, wchar_t *out) {
    wchar_t buffer[39];
    int i;
    if (!compressed || wcslen(compressed) != 25) return 0;
    ZeroMemory(buffer, sizeof(buffer));
    buffer[0] = L'{';
    buffer[9] = L'-';
    buffer[14] = L'-';
    buffer[19] = L'-';
    buffer[24] = L'-';
    buffer[37] = L'}';
    for (i = 0; i < 20; i++) {
        int offset = i < 8 ? i + 1 : i < 12 ? i + 2 : i < 16 ? i + 3 : i + 4;
        buffer[offset] = compressed[19 - i];
    }
    for (i = 20; i < 25; i++) {
        buffer[i + 9] = compressed[i];
    }
    buffer[38] = 0;
    wcscpy_s(out, 40, buffer);
    return 1;
}

static void rename_programs_entry(const char *version) {
    HKEY up;
    DWORD index = 0;
    wchar_t name[64];
    DWORD name_cch;
    wchar_t product[40];
    wchar_t sub[256];
    wchar_t wide_ver[32];
    char core[32];
    HKEY un;
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, UPGRADE_KEY, 0, KEY_READ, &up) != ERROR_SUCCESS) {
        return;
    }
    core_version(version, core, sizeof(core));
    if (!core[0]) {
        strncpy_s(core, sizeof(core), version ? version : "", _TRUNCATE);
    }
    for (;;) {
        name_cch = 64;
        if (RegEnumValueW(up, index, name, &name_cch, NULL, NULL, NULL, NULL) != ERROR_SUCCESS) break;
        index++;
        if (!decompress_product_code(name, product)) continue;
        _snwprintf_s(sub, 256, _TRUNCATE, L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\%s", product);
        if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, sub, 0, KEY_SET_VALUE, &un) != ERROR_SUCCESS) continue;
        RegSetValueExW(un, L"DisplayName", 0, REG_SZ, (const BYTE *)L"bADagent", (DWORD)((wcslen(L"bADagent") + 1) * sizeof(wchar_t)));
        MultiByteToWideChar(CP_UTF8, 0, core, -1, wide_ver, 32);
        RegSetValueExW(un, L"DisplayVersion", 0, REG_SZ, (const BYTE *)wide_ver, (DWORD)((wcslen(wide_ver) + 1) * sizeof(wchar_t)));
        RegCloseKey(un);
        break;
    }
    RegCloseKey(up);
}

static void retarget_service(void) {
    SC_HANDLE scm, svc;
    scm = OpenSCManagerW(NULL, NULL, SC_MANAGER_CONNECT);
    if (!scm) return;
    svc = OpenServiceW(scm, L"bADagent", SERVICE_CHANGE_CONFIG);
    if (svc) {
        ChangeServiceConfigW(svc, SERVICE_NO_CHANGE, SERVICE_NO_CHANGE, SERVICE_NO_CHANGE,
            IMAGE_PATH, NULL, NULL, NULL, NULL, NULL, NULL);
        CloseServiceHandle(svc);
    }
    CloseServiceHandle(scm);
}

static void restart_service(void) {
    SC_HANDLE scm, svc;
    SERVICE_STATUS st;
    DWORD i;
    scm = OpenSCManagerW(NULL, NULL, SC_MANAGER_CONNECT);
    if (!scm) return;
    svc = OpenServiceW(scm, L"bADagent", SERVICE_START | SERVICE_STOP | SERVICE_QUERY_STATUS);
    if (!svc) {
        CloseServiceHandle(scm);
        return;
    }
    QueryServiceStatus(svc, &st);
    if (st.dwCurrentState != SERVICE_STOPPED) {
        ControlService(svc, SERVICE_CONTROL_STOP, &st);
        for (i = 0; i < 60; i++) {
            Sleep(500);
            if (!QueryServiceStatus(svc, &st)) break;
            if (st.dwCurrentState == SERVICE_STOPPED) break;
        }
    }
    StartServiceW(svc, 0, NULL);
    CloseServiceHandle(svc);
    CloseServiceHandle(scm);
}

static void spawn_restarter(void) {
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    wchar_t cmd[MAX_PATH + 8];
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    ZeroMemory(&pi, sizeof(pi));
    _snwprintf_s(cmd, MAX_PATH + 8, _TRUNCATE, L"\"%s\"", LINK_EXE);
    if (CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
    }
}

static int post_enrollment(const wchar_t *server, char *api_key, char *bad_id, char *signing, char *arc_pw, char *arc_sha, char *arc_ver) {
    char host[256], ip[64], serial[256], fp[80], guid[128], uuid[80];
    char eh[300], ei[80], es[300], efp[80], eg[140], eu[100];
    char body[1600];
    wchar_t url[1200];
    char *resp = NULL;
    char status[32];
    api_key[0] = bad_id[0] = signing[0] = arc_pw[0] = arc_sha[0] = arc_ver[0] = 0;
    if (!fingerprint_hex(fp, sizeof(fp))) return 0;
    read_hostname(host, sizeof(host));
    read_ip(ip, sizeof(ip));
    read_serial(serial, sizeof(serial));
    json_escape(host, eh, sizeof(eh));
    json_escape(ip, ei, sizeof(ei));
    json_escape(serial, es, sizeof(es));
    json_escape(fp, efp, sizeof(efp));
    if (read_smbios(uuid, sizeof(uuid)) && uuid[0]) {
        read_machine_guid(guid, sizeof(guid));
        json_escape(guid, eg, sizeof(eg));
        json_escape(uuid, eu, sizeof(eu));
        _snprintf_s(body, sizeof(body), _TRUNCATE,
            "{\"hostname\":\"%s\",\"ip\":\"%s\",\"serial\":\"%s\",\"fingerprint\":\"%s\",\"machine_guid\":\"%s\",\"smbios_uuid\":\"%s\"}",
            eh, ei, es, efp, eg, eu);
    } else {
        _snprintf_s(body, sizeof(body), _TRUNCATE,
            "{\"hostname\":\"%s\",\"ip\":\"%s\",\"serial\":\"%s\",\"fingerprint\":\"%s\"}",
            eh, ei, es, efp);
    }
    join_url(server, "/v1/enrollment-requests", url, 1200);
    if (!http_call(url, L"POST", NULL, body, &resp)) return 0;
    json_string(resp, "status", status, sizeof(status));
    if (_stricmp(status, "approved") == 0) {
        json_string(resp, "api_key", api_key, 512);
        json_string(resp, "bad_id", bad_id, 64);
        json_string(resp, "signing_key", signing, 256);
        json_string(resp, "archive_password", arc_pw, 256);
        json_string(resp, "archive_sha256", arc_sha, 80);
        json_string(resp, "archive_version", arc_ver, 64);
    }
    free(resp);
    return _stricmp(status, "approved") == 0 && api_key[0] && signing[0];
}

static int poll_archive(const wchar_t *server, const char *api_key, char *url_path, char *sha, char *password, char *version) {
    wchar_t url[1200];
    char *resp = NULL;
    url_path[0] = sha[0] = password[0] = 0;
    join_url(server, "/v1/agent/update/check?current=0.0.0", url, 1200);
    if (!http_call(url, L"GET", api_key, NULL, &resp)) return 0;
    json_string(resp, "url", url_path, 512);
    json_string(resp, "archive_sha256", sha, 80);
    json_string(resp, "archive_password", password, 256);
    if (version && !version[0]) {
        json_string(resp, "version", version, 64);
        if (!version[0]) json_string(resp, "target_version", version, 64);
    }
    free(resp);
    return url_path[0] && sha[0] && password[0];
}

static int apply_archive(const wchar_t *server, const char *api_key, const char *version, const char *sha, const char *password, const char *url_path) {
    wchar_t url[1200];
    wchar_t arc[MAX_PATH], zip[MAX_PATH];
    char got[80];
    wchar_t tmpdir[MAX_PATH];
    char path[256];
    GetTempPathW(MAX_PATH, tmpdir);
    _snwprintf_s(arc, MAX_PATH, _TRUNCATE, L"%sbad-agent-download.arc", tmpdir);
    _snwprintf_s(zip, MAX_PATH, _TRUNCATE, L"%sbad-agent-download.zip", tmpdir);
    if (url_path && url_path[0]) {
        if (strncmp(url_path, "https://", 8) == 0) {
            wchar_t *w = utf8_to_wide(url_path);
            if (!w || _wcsnicmp(w, server, wcslen(server)) != 0) {
                free(w);
                _snprintf_s(path, sizeof(path), _TRUNCATE, "/v1/agent/update/archive?version=%s", version);
                join_url(server, path, url, 1200);
            } else {
                wcsncpy_s(url, 1200, w, _TRUNCATE);
                free(w);
            }
        } else {
            join_url(server, url_path, url, 1200);
        }
    } else {
        _snprintf_s(path, sizeof(path), _TRUNCATE, "/v1/agent/update/archive?version=%s", version);
        join_url(server, path, url, 1200);
    }
    if (!starts_https(url)) return 0;
    if (!download_file(url, api_key, arc)) return 0;
    if (!sha256_file(arc, got, sizeof(got)) || !hex_eq(got, sha)) {
        DeleteFileW(arc);
        return 0;
    }
    if (!decrypt_arc(arc, password, zip)) {
        DeleteFileW(arc);
        return 0;
    }
    DeleteFileW(arc);
    if (!unzip_to_bin(zip)) {
        DeleteFileW(zip);
        return 0;
    }
    DeleteFileW(zip);
    return file_exists(AGENT_EXE);
}

static void work(void) {
    wchar_t server[1024];
    char api_key[512], bad_id[64], signing[256];
    char arc_pw[256], arc_sha[80], arc_ver[64], url_path[512];
    int have_keys = 0;
    api_key[0] = bad_id[0] = signing[0] = 0;
    arc_pw[0] = arc_sha[0] = arc_ver[0] = url_path[0] = 0;
    for (;;) {
        if (stopped()) return;
        ensure_server_url(server, 1024);
        if (!starts_https(server)) {
            if (wait_ms(15000)) return;
            continue;
        }
        if (!have_keys) {
            if (post_enrollment(server, api_key, bad_id, signing, arc_pw, arc_sha, arc_ver)) {
                save_secrets(server, api_key, bad_id, signing);
                have_keys = 1;
            } else {
                if (wait_ms(15000)) return;
                continue;
            }
        }
        if (!(arc_pw[0] && arc_sha[0] && (arc_ver[0] || url_path[0]))) {
            if (!poll_archive(server, api_key, url_path, arc_sha, arc_pw, arc_ver)) {
                if (wait_ms(15000)) return;
                continue;
            }
        }
        if (!apply_archive(server, api_key, arc_ver[0] ? arc_ver : "0.0.0", arc_sha, arc_pw, url_path[0] ? url_path : NULL)) {
            SecureZeroMemory(arc_pw, sizeof(arc_pw));
            arc_pw[0] = 0;
            if (wait_ms(15000)) return;
            continue;
        }
        SecureZeroMemory(arc_pw, sizeof(arc_pw));
        retarget_service();
        rename_programs_entry(arc_ver[0] ? arc_ver : arc_sha);
        spawn_restarter();
        return;
    }
}

static void WINAPI ServiceMain(DWORD argc, LPWSTR *argv) {
    (void)argc;
    (void)argv;
    g_status_handle = RegisterServiceCtrlHandlerExW(L"bADagent", handler, NULL);
    report(SERVICE_START_PENDING);
    g_stop = CreateEventW(NULL, TRUE, FALSE, NULL);
    report(SERVICE_RUNNING);
    work();
    report(SERVICE_STOPPED);
    if (g_stop) CloseHandle(g_stop);
}

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE prev, LPWSTR cmd, int show) {
    SERVICE_TABLE_ENTRYW table[2];
    (void)inst;
    (void)prev;
    (void)cmd;
    (void)show;
    table[0].lpServiceName = L"bADagent";
    table[0].lpServiceProc = ServiceMain;
    table[1].lpServiceName = NULL;
    table[1].lpServiceProc = NULL;
    if (!StartServiceCtrlDispatcherW(table)) {
        if (GetLastError() == ERROR_FAILED_SERVICE_CONTROLLER_CONNECT && file_exists(AGENT_EXE)) {
            restart_service();
        }
    }
    return 0;
}
