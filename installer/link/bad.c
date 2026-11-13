#include <windows.h>
#include <stdio.h>
#include <string.h>

#pragma comment(lib, "shell32.lib")

#define AGENT_EXE L"C:\\Program Files\\blazerity\\bADagent\\bin\\BadAgent.exe"
#define CONFIG_PATH L"C:\\ProgramData\\blazerity\\bADagent\\config.json"
#define STATUS_PATH L"C:\\ProgramData\\blazerity\\bADagent\\link-status.txt"

static int file_exists(const wchar_t *path) {
    DWORD attr = GetFileAttributesW(path);
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

static int computer_name(COMPUTER_NAME_FORMAT fmt, wchar_t *out, DWORD cch) {
    DWORD n = cch;
    out[0] = 0;
    if (!GetComputerNameExW(fmt, out, &n) || !out[0]) {
        out[0] = 0;
        return 0;
    }
    return 1;
}

static void read_hostname(wchar_t *out, size_t cch) {
    wchar_t fqdn[256], host[256], domain[256];
    out[0] = 0;
    if (computer_name(ComputerNameDnsFullyQualified, fqdn, 256) && wcschr(fqdn, L'.')) {
        wcsncpy_s(out, cch, fqdn, _TRUNCATE);
        return;
    }
    if (!computer_name(ComputerNameDnsHostname, host, 256)) return;
    if (computer_name(ComputerNameDnsDomain, domain, 256)) {
        _snwprintf_s(out, cch, _TRUNCATE, L"%s.%s", host, domain);
    } else {
        wcsncpy_s(out, cch, host, _TRUNCATE);
    }
}

static void json_string(const char *json, const char *key, char *out, size_t cch) {
    char pat[80];
    const char *p;
    size_t j = 0;
    out[0] = 0;
    if (!json || !key || cch == 0) return;
    _snprintf_s(pat, sizeof(pat), _TRUNCATE, "\"%s\"", key);
    p = strstr(json, pat);
    if (!p) return;
    p += strlen(pat);
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
    if (*p != ':') return;
    p++;
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
    if (*p != '"') return;
    p++;
    while (*p && *p != '"' && j + 1 < cch) {
        if (*p == '\\' && p[1]) p++;
        out[j++] = *p++;
    }
    out[j] = 0;
}

static void read_server(wchar_t *out, size_t cch) {
    HANDLE h;
    DWORD size, read = 0;
    char *buf;
    char url[1024];
    out[0] = 0;
    h = CreateFileW(CONFIG_PATH, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    size = GetFileSize(h, NULL);
    if (size == 0 || size > 1024 * 1024) {
        CloseHandle(h);
        return;
    }
    buf = (char *)malloc((size_t)size + 1);
    if (!buf || !ReadFile(h, buf, size, &read, NULL)) {
        free(buf);
        CloseHandle(h);
        return;
    }
    buf[read] = 0;
    CloseHandle(h);
    json_string(buf, "server_url", url, sizeof(url));
    free(buf);
    if (!url[0]) return;
    MultiByteToWideChar(CP_UTF8, 0, url, -1, out, (int)cch);
}

static void read_status(char *out, size_t cch) {
    HANDLE h;
    DWORD read = 0;
    size_t i;
    out[0] = 0;
    h = CreateFileW(STATUS_PATH, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    if (!ReadFile(h, out, (DWORD)(cch - 1), &read, NULL)) {
        CloseHandle(h);
        out[0] = 0;
        return;
    }
    CloseHandle(h);
    out[read] = 0;
    for (i = 0; out[i] && out[i] != '\n' && out[i] != '\r'; i++) {
    }
    out[i] = 0;
}

static void write_out(const wchar_t *text) {
    HANDLE h = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD mode = 0, wrote = 0;
    char buf[1200];
    int n;
    if (h != INVALID_HANDLE_VALUE && GetConsoleMode(h, &mode)) {
        WriteConsoleW(h, text, (DWORD)wcslen(text), &wrote, NULL);
        WriteConsoleW(h, L"\n", 1, &wrote, NULL);
        return;
    }
    n = WideCharToMultiByte(CP_UTF8, 0, text, -1, buf, (int)sizeof(buf), NULL, NULL);
    if (n > 1) {
        fwrite(buf, 1, (size_t)(n - 1), stdout);
        fputc('\n', stdout);
    }
}

static void print_field(const wchar_t *field, const wchar_t *value) {
    wchar_t line[700];
    size_t n = wcslen(field);
    if (n >= 16) {
        _snwprintf_s(line, 700, _TRUNCATE, L"%s  %s", field, value ? value : L"");
    } else {
        _snwprintf_s(line, 700, _TRUNCATE, L"%s%*s%s", field, (int)(16 - n), L"", value ? value : L"");
    }
    write_out(line);
}

static int status_fails(const char *line) {
    if (!line) return 0;
    if (strcmp(line, "нет связи") == 0) return 1;
    if (strcmp(line, "не сошлась контрольная сумма") == 0) return 1;
    if (strcmp(line, "не расшифровался архив") == 0) return 1;
    if (strcmp(line, "не распаковался архив") == 0) return 1;
    if (strcmp(line, "служба не переключилась") == 0) return 1;
    return 0;
}

static int print_info(void) {
    wchar_t host[512], server[1024], link[400];
    char status[320];
    read_hostname(host, 512);
    read_server(server, 1024);
    read_status(status, sizeof(status));
    link[0] = 0;
    if (status[0]) {
        MultiByteToWideChar(CP_UTF8, 0, status, -1, link, 400);
    }
    print_field(L"Версия", L"1.0.0");
    print_field(L"Сервер", server);
    print_field(L"Hostname", host);
    print_field(L"bad_id", L"");
    print_field(L"Модель", L"");
    print_field(L"Связь", link);
    return status_fails(status) ? 1 : 0;
}

static void append_quoted(wchar_t *cmd, size_t cch, const wchar_t *arg) {
    size_t i;
    wcsncat_s(cmd, cch, L" \"", _TRUNCATE);
    for (i = 0; arg[i]; i++) {
        wchar_t one[3];
        if (arg[i] == L'"') {
            wcsncat_s(cmd, cch, L"\\\"", _TRUNCATE);
        } else {
            one[0] = arg[i];
            one[1] = 0;
            wcsncat_s(cmd, cch, one, _TRUNCATE);
        }
    }
    wcsncat_s(cmd, cch, L"\"", _TRUNCATE);
}

static int run_agent(int argc, wchar_t **argv) {
    wchar_t cmd[32768];
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD code = 1;
    int i;
    cmd[0] = 0;
    wcsncat_s(cmd, 32768, L"\"", _TRUNCATE);
    wcsncat_s(cmd, 32768, AGENT_EXE, _TRUNCATE);
    wcsncat_s(cmd, 32768, L"\"", _TRUNCATE);
    for (i = 1; i < argc; i++) {
        append_quoted(cmd, 32768, argv[i]);
    }
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    if (!CreateProcessW(NULL, cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
        return 1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)code;
}

int main(void) {
    int argc = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    int code;
    if (!argv) return 2;
    if (file_exists(AGENT_EXE)) {
        code = run_agent(argc, argv);
        LocalFree(argv);
        return code;
    }
    if (argc >= 2 && _wcsicmp(argv[1], L"info") == 0) {
        code = print_info();
        LocalFree(argv);
        return code;
    }
    write_out(L"агент ещё не установлен");
    LocalFree(argv);
    return 2;
}
