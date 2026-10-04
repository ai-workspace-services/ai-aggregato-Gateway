-- Run the generated access function with a fake HTTP request and upstream.
-- This verifies routing/body/header behavior, not native APISIX authentication.
local json = require('cjson.safe')
local source = assert(io.open(arg[1])):read('*a')
local handler = assert(loadstring(source))()
local selected, body, headers, method
ngx = {var={}, header={}, req={}}
ngx.req.get_method = function() return method end
ngx.req.set_body_data = function(value) body = value end
ngx.req.set_header = function(key, value) headers[key] = value end
ngx.req.clear_header = function(key) headers[key] = nil end
package.loaded['apisix.core'] = {
    json=json, request={get_body=function() return body end},
}
package.loaded['apisix.upstream'] = {
    set=function(ctx, key, version, conf) selected = conf end,
}
local function request(path, verb, model)
    selected = nil
    ngx.var.uri, method = path, verb
    body = json.encode({model=model, messages={{role='user',content='hello'}}})
    headers = {apikey='fixture-client', Cookie='fixture-cookie', Authorization='Bearer fixture-client'}
    return handler({}, {var={}})
end
local code, catalog = request('/v1/models', 'GET')
assert(code == 200 and #catalog.data == 2)
assert(catalog.data[1].id == 'gpt-test')
assert(catalog.data[1].owned_by == 'ai-gateway')
code = request('/v1/chat/completions', 'POST', 'gpt-test')
assert(code == nil and selected.nodes[1].port == 8317 and selected.retries == 0)
assert(json.decode(body).model == 'gpt-test')
assert(headers.apikey == nil and headers.Cookie == nil)
assert(headers.Authorization == 'Bearer fixture-only')
code = request('/v1/chat/completions', 'POST', 'official-test')
assert(code == nil and selected.nodes[1].port == 4000)
assert(headers.Authorization == 'Bearer fixture-official')
assert(request('/v1/messages', 'POST', 'gpt-test') == 400)
assert(request('/v1/chat/completions', 'POST', 'unknown') == 403)
assert(request('/v1/unknown', 'POST', 'gpt-test') == 404)
assert(request('/v1/responses', 'GET', 'gpt-test') == 405)
print('7 Lua routing checks passed; no upstream calls or credentials displayed')
