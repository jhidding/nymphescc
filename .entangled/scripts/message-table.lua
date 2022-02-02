-- Extracts message information from messaged.md

-- Current location in document
location = {}

-- Current setting
setting = nil

groups = {}

schema = nil

function current_group()
    return groups[format_location(location)]
end

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
        push()
        if not location then
            location = {}
        end
        location[el.level] = el.attributes["name"]
        -- new group also means clearing child headers
        for i = (el.level+1), max_key(location) do
            location[i] = nil
        end
        loc = format_location(location)
        groups[loc] = { long = trim(pandoc.write(pandoc.Pandoc(pandoc.Para(el.content)), "plain"))
                      , content = {} }
        -- table.insert(document, shallow_copy(location))
    elseif contains(el.classes, "setting") then
        if setting then
            push()
        end        
        el.attributes["long"] = trim(pandoc.write(pandoc.Pandoc(pandoc.Para(el.content)), "plain"))
        setting = { attr = el.attributes }
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

function add_to_description(item, what)
    content = trim(pandoc.write(pandoc.Pandoc{what}, "plain"))
    if not item.description then
        item.description = content
    else
        item.description = item.description .. "\n\n" .. content
    end
end

function Para(el)
    if setting then
        add_to_description(setting, el)
    elseif current_group() then
        add_to_description(current_group(), el)
    end
end

function BulletList(el)
    Para(el)
end

function push()
    if not setting or not location then
        return
    end

    -- local loc = format_location(location)
    local group = current_group()
    table.insert(group.content, setting)
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
        if not tonumber(v) then
            v = "\"" .. v .. "\""
        end
        if k == "mod" then
            v = "Some " .. v
        end
        table.insert(x, k .. " = " .. v)
    end
    return "{ " .. table.concat(x, ", ") .. " }"
end

function format_setting(item)
    record = schema
        .. "in " 
        .. format_table(item.attr)
        .. (item.extra and (" // " .. item.extra) or "")
        .. (item.description and (" // { description = Some ''\n" .. item.description .. "\n'' }") or "")
    joined = pandoc.pipe("dhall", {}, record)
    return "Setting :: " .. joined
end

function format_group(name, grp)
    return "{ name = \"" .. name .. "\"\n"
        .. ", long = \"" .. grp.long .. "\"\n"
        .. ", description = "
            .. (grp.description and ("Some ''\n"
            ..  grp.description .. "\n''\n") or "None Text\n")
        .. ", content =\n[ " 
        .. table.concat(map(format_setting, grp.content), "\n, ")
        .. "] : List Setting.Type }"
end

function map_table(f, tbl)
    local t = {}
    for k, v in pairs(tbl) do
        table.insert(t, f(k, v))
    end
    return t
end

function format_document()
    return "[ " .. table.concat(map_table(format_group, groups), "\n, ") .. "\n]"
end

function format_location(loc)
    return table.concat(loc, ".", min_key(loc), max_key(loc))
end

function Pandoc(el)
    push()
    text = "-- generated by Pandoc, don't edit this!\n"
        .. schema .. "\nin " .. format_document()
    print(text)
    return pandoc.Pandoc({}) -- pandoc.Plain(text))
end