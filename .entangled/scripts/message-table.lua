-- Extracts message information from messaged.md

-- Current location in document
location = {}

-- Current setting
setting = nil

-- Document tree
document = { _type = "group", _name = "root" }

schema = nil

function contains(list, x)
	for _, v in pairs(list) do
		if v == x then return true end
	end
	return false
end

function shallow_copy(tbl)
    local t = {}
    for k, v in pairs(tbl) do
        t[k] = v
    end
    return t
end

function map(f, lst)
    local t = {}
    for k, v in pairs(lst) do
        t[k] = f(v)
    end
    return t
end

function trim(s)
    return (s:gsub("^%s*(.-)%s*$", "%1"))
end

function table.values(tbl)
    local t = {}
    for _, v in pairs(tbl) do
        table.insert(t, v)
    end
    return t
end

function Header(el)
    if contains(el.classes, "group") then
        if not location then
            location = {}
        end
        location[el.level] = el.attributes["name"]
        -- new group also means clearing child headers
        for i = (el.level+1), max_key(location) do
            location[i] = nil
        end
        -- table.insert(document, shallow_copy(location))
    elseif contains(el.classes, "setting") then
        location[el.level] = el.attributes["name"]
        if setting then
            push()
        end
        setting = { attr = el.attributes }
    else
        location = nil
    end
end

function CodeBlock(el)
    if el.identifier == "schema" then
        schema = el.text
    end
    if contains(el.classes, "values") then
        setting.extra = string.gsub(el.text, "\n", " ")
    end
end

function Para(el)
    if not setting or not location then
        return
    end
    content = trim(pandoc.write(pandoc.Pandoc{el}, "plain"))
    if not setting.description then
        setting.description = content
    else
        setting.description = setting.description .. "\n\n" .. content
    end
end

function push()
    if not setting or not location then
        return
    end

    local r = document
    for _, v in pairs(location) do
        if not r[v] then
            r[v] = { _type = "group", _name = v }
        end
        r = r[v]
    end
    r._type = "setting"
    for k, v in pairs(setting) do
        r[k] = v
    end
    setting = nil
end

function min_key(tbl)
    local r = 1000
    for k, _ in pairs(tbl) do
        r = math.min(r, k)
    end
    return r
end

function max_key(tbl)
    local r = 0
    for k, _ in pairs(tbl) do
        r = math.max(r, k)
    end
    return r
end

function format_table(tbl)
    if not tbl then
        return "{}"
    end
    x = {}
    for k, v in pairs(tbl) do
        table.insert(x, k .. " = " .. v)
    end
    return "{ " .. table.concat(x, ", ") .. " }"
end

function format_document(item)
    if item._type == "group" then
        return "Node.Group { name = \"" .. item._name .. "\"\n"
            .. ", contents = [" .. table.concat(table.values(map(format_document, item)), "\n            , ")
            .. "             ]\n"
            .. "}"
    elseif item._type == "setting" then
        local d = "None Text"
        if item.description then
            d = "Some ''\n" .. item.description .. "\n''"
        end
        return "Node.Setting (Setting :: ( { description = " .. d .. " } // " 
            .. format_table(item.attr) 
            .. (item.extra and (" // " .. item.extra) or "") 
            .. "))"
    else
        return nil
    end
end

function format_location(loc)
    return table.concat(loc, ".", min_key(loc), max_key(loc))
end

function Pandoc(el)
    push()
    text = schema .. "\nin " .. format_document(document)
    print(text)
    return pandoc.Pandoc({}) -- pandoc.Plain(text))
end
