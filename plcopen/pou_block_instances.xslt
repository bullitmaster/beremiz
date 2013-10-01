<xsl:stylesheet xmlns:func="http://exslt.org/functions" xmlns:dyn="http://exslt.org/dynamic" xmlns:str="http://exslt.org/strings" xmlns:math="http://exslt.org/math" xmlns:exsl="http://exslt.org/common" extension-element-prefixes="ns" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:yml="http://fdik.org/yml" xmlns:set="http://exslt.org/sets" version="1.0" xmlns:ppx="http://www.plcopen.org/xml/tc6_0201" xmlns:ns="pou_block_instances_ns" exclude-result-prefixes="ns" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"><xsl:output method="xml"/><xsl:variable name="space" select="'                                                                                                                                                                                                        '"/><xsl:param name="autoindent" select="4"/><xsl:template match="text()"><xsl:param name="_indent" select="0"/></xsl:template><xsl:template match="ppx:pou"><xsl:param name="_indent" select="0"/><xsl:apply-templates select="ppx:body/*[self::ppx:FBD or self::ppx:LD or self::ppx:SFC]/*"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template name="add_instance"><xsl:param name="_indent" select="0"/><xsl:param name="type"/><xsl:variable name="instance"><xsl:value-of select="ns:AddBlockInstance($type, @localId, ppx:position/@x, ppx:position/@y, @width, @height)"/></xsl:variable></xsl:template><xsl:template name="execution_order"><xsl:param name="_indent" select="0"/><xsl:choose><xsl:when test="@executionOrderId"><xsl:value-of select="@executionOrderId"/></xsl:when><xsl:otherwise><xsl:text>0</xsl:text></xsl:otherwise></xsl:choose></xsl:template><xsl:template name="ConnectionInfos"><xsl:param name="_indent" select="0"/><xsl:param name="type"/><xsl:param name="modifiers"/><xsl:param name="formalParameter"/><xsl:variable name="negated"><xsl:choose><xsl:when test="$modifiers='input'"><xsl:value-of select="@negatedIn"/></xsl:when><xsl:when test="$modifiers='output'"><xsl:value-of select="@negatedOut"/></xsl:when><xsl:otherwise><xsl:value-of select="@negated"/></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="edge"><xsl:choose><xsl:when test="$modifiers='input'"><xsl:value-of select="@edgeIn"/></xsl:when><xsl:when test="$modifiers='output'"><xsl:value-of select="@edgeOut"/></xsl:when><xsl:otherwise><xsl:value-of select="@edge"/></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="instance_connection"><xsl:value-of select="ns:AddInstanceConnection($type, $formalParameter, $negated, $edge, ppx:relPosition/@x, ppx:relPosition/@y)"/></xsl:variable></xsl:template><xsl:template match="ppx:position"><xsl:param name="_indent" select="0"/><xsl:variable name="link_point"><xsl:value-of select="ns:AddLinkPoint(@x, @y)"/></xsl:variable></xsl:template><xsl:template match="ppx:connection"><xsl:param name="_indent" select="0"/><xsl:variable name="connection_link"><xsl:value-of select="ns:AddConnectionLink(@refLocalId, @formalParameter)"/></xsl:variable><xsl:apply-templates select="ppx:position"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:connectionPointIn"><xsl:param name="_indent" select="0"/><xsl:param name="modifiers"/><xsl:param name="formalParameter"/><xsl:call-template name="ConnectionInfos"><xsl:with-param name="type"><xsl:text>input</xsl:text></xsl:with-param><xsl:with-param name="modifiers"><xsl:value-of select="$modifiers"/></xsl:with-param><xsl:with-param name="formalParameter"><xsl:value-of select="$formalParameter"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connection"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:connectionPointOut"><xsl:param name="_indent" select="0"/><xsl:param name="modifiers"/><xsl:param name="formalParameter"/><xsl:call-template name="ConnectionInfos"><xsl:with-param name="type"><xsl:text>output</xsl:text></xsl:with-param><xsl:with-param name="modifiers"><xsl:value-of select="$modifiers"/></xsl:with-param><xsl:with-param name="formalParameter"><xsl:value-of select="$formalParameter"/></xsl:with-param></xsl:call-template></xsl:template><xsl:template match="ppx:connectionPointOutAction"><xsl:param name="_indent" select="0"/><xsl:call-template name="ConnectionInfos"><xsl:with-param name="type"><xsl:text>output</xsl:text></xsl:with-param></xsl:call-template></xsl:template><xsl:template match="ppx:comment"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues(ppx:content/xhtml:p/text())"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template></xsl:template><xsl:template match="ppx:block"><xsl:param name="_indent" select="0"/><xsl:variable name="execution_order"><xsl:call-template name="execution_order"></xsl:call-template></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues(@instanceName, $execution_order)"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="@typeName"/></xsl:with-param></xsl:call-template><xsl:for-each select="ppx:inputVariables/ppx:variable"><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/><xsl:with-param name="formalParameter"><xsl:value-of select="@formalParameter"/></xsl:with-param></xsl:apply-templates></xsl:for-each><xsl:for-each select="ppx:outputVariables/ppx:variable"><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/><xsl:with-param name="formalParameter"><xsl:value-of select="@formalParameter"/></xsl:with-param></xsl:apply-templates></xsl:for-each></xsl:template><xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:derived"><xsl:param name="_indent" select="0"/><xsl:value-of select="@name"/></xsl:template><xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:string"><xsl:param name="_indent" select="0"/><xsl:text>STRING</xsl:text></xsl:template><xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:wstring"><xsl:param name="_indent" select="0"/><xsl:text>WSTRING</xsl:text></xsl:template><xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/*"><xsl:param name="_indent" select="0"/><xsl:value-of select="local-name()"/></xsl:template><xsl:template name="VariableBlockInfos"><xsl:param name="_indent" select="0"/><xsl:param name="type"/><xsl:variable name="expression"><xsl:value-of select="ppx:expression/text()"/></xsl:variable><xsl:variable name="value_type"><xsl:choose><xsl:when test="ancestor::ppx:transition[@name=$expression]"><xsl:text>BOOL</xsl:text></xsl:when><xsl:when test="ancestor::ppx:pou[@name=$expression]"><xsl:apply-templates select="ancestor::ppx:pou/child::ppx:interface/ppx:returnType"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:when><xsl:otherwise><xsl:apply-templates select="ancestor::ppx:pou/child::ppx:interface/*/ppx:variable[@name=$expression]/ppx:type"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="execution_order"><xsl:call-template name="execution_order"></xsl:call-template></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues($expression, $value_type, $execution_order)"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/><xsl:with-param name="modifiers"><xsl:choose><xsl:when test="$type='inout'"><xsl:text>input</xsl:text></xsl:when><xsl:otherwise></xsl:otherwise></xsl:choose></xsl:with-param></xsl:apply-templates><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/><xsl:with-param name="modifiers"><xsl:choose><xsl:when test="$type='inout'"><xsl:text>output</xsl:text></xsl:when><xsl:otherwise></xsl:otherwise></xsl:choose></xsl:with-param></xsl:apply-templates></xsl:template><xsl:template match="ppx:inVariable"><xsl:param name="_indent" select="0"/><xsl:call-template name="VariableBlockInfos"><xsl:with-param name="type" select="'input'"/></xsl:call-template></xsl:template><xsl:template match="ppx:outVariable"><xsl:param name="_indent" select="0"/><xsl:call-template name="VariableBlockInfos"><xsl:with-param name="type" select="'output'"/></xsl:call-template></xsl:template><xsl:template match="ppx:inOutVariable"><xsl:param name="_indent" select="0"/><xsl:call-template name="VariableBlockInfos"><xsl:with-param name="type" select="'inout'"/></xsl:call-template></xsl:template><xsl:template match="ppx:connector|ppx:continuation"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues(@name)"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:leftPowerRail|ppx:rightPowerRail"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="connectors"><xsl:choose><xsl:when test="$type='leftPowerRail'"><xsl:value-of select="count(ppx:connectionPointOut)"/></xsl:when><xsl:otherwise><xsl:value-of select="count(ppx:connectionPointIn)"/></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues($connectors)"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:choose><xsl:when test="$type='leftPowerRail'"><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:when><xsl:otherwise><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:otherwise></xsl:choose></xsl:template><xsl:template match="ppx:contact|ppx:coil"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="storage"><xsl:choose><xsl:when test="$type='coil'"><xsl:value-of select="@storage"/></xsl:when><xsl:otherwise></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="execution_order"><xsl:call-template name="execution_order"></xsl:call-template></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues(ppx:variable/text(), @negated, @edge, $storage, $execution_order)"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:step"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues(@name, @initialStep)"/></xsl:variable><xsl:apply-templates select="ppx:connectionPointOutAction"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:transition"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="priority"><xsl:choose><xsl:when test="@priority"><xsl:value-of select="@priority"/></xsl:when><xsl:otherwise><xsl:text>0</xsl:text></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="condition_type"><xsl:choose><xsl:when test="ppx:condition/ppx:connectionPointIn"><xsl:text>connection</xsl:text></xsl:when><xsl:when test="ppx:condition/ppx:reference"><xsl:text>reference</xsl:text></xsl:when><xsl:when test="ppx:condition/ppx:inline"><xsl:text>inline</xsl:text></xsl:when><xsl:otherwise></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="condition"><xsl:choose><xsl:when test="ppx:reference"><xsl:value-of select="ppx:condition/ppx:reference/@name"/></xsl:when><xsl:when test="ppx:inline"><xsl:value-of select="ppx:condition/ppx:inline/ppx:body/ppx:ST/xhtml:p/text()"/></xsl:when><xsl:otherwise></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues($priority, $condition_type, $condition)"/></xsl:variable><xsl:apply-templates select="ppx:condition/ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:selectionDivergence|ppx:selectionConvergence|ppx:simultaneousDivergence|ppx:simultaneousConvergence"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="connectors"><xsl:choose><xsl:when test="ppx:selectionDivergence|ppx:simultaneousDivergence"><xsl:value-of select="count(ppx:connectionPointOut)"/></xsl:when><xsl:otherwise><xsl:value-of select="count(ppx:connectionPointIn)"/></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues($connectors)"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:apply-templates select="ppx:connectionPointOut"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:jumpStep"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:text>jump</xsl:text></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues(@targetName)"/></xsl:variable><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template><xsl:template match="ppx:action"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:choose><xsl:when test="ppx:reference"><xsl:text>reference</xsl:text></xsl:when><xsl:when test="ppx:inline"><xsl:text>inline</xsl:text></xsl:when><xsl:otherwise></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="value"><xsl:choose><xsl:when test="ppx:reference"><xsl:value-of select="ppx:reference/@name"/></xsl:when><xsl:when test="ppx:inline"><xsl:value-of select="ppx:inline/ppx:ST/xhtml:p/text()"/></xsl:when><xsl:otherwise></xsl:otherwise></xsl:choose></xsl:variable><xsl:variable name="actionBlock_action"><xsl:value-of select="ns:AddAction(@qualifier, $type, $value, @duration, @indicator)"/></xsl:variable></xsl:template><xsl:template match="ppx:actionBlock"><xsl:param name="_indent" select="0"/><xsl:variable name="type"><xsl:value-of select="local-name()"/></xsl:variable><xsl:variable name="instance_specific_values"><xsl:value-of select="ns:SetSpecificValues()"/></xsl:variable><xsl:apply-templates select="ppx:action"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates><xsl:call-template name="add_instance"><xsl:with-param name="type"><xsl:value-of select="$type"/></xsl:with-param></xsl:call-template><xsl:apply-templates select="ppx:connectionPointIn"><xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/></xsl:apply-templates></xsl:template></xsl:stylesheet>