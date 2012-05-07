from ..toolchain_gcc import toolchain_gcc

class Xenomai_target(toolchain_gcc):
    extension = ".so"
    def getXenoConfig(self, flagsname):
        """ Get xeno-config from target parameters """
        xeno_config=self.ConfigTreeRootInstance.GetTarget().getcontent()["value"].getXenoConfig()
        if xeno_config:
            from wxPopen import ProcessLogger
            status, result, err_result = ProcessLogger(self.ConfigTreeRootInstance.logger,
                                                       xeno_config + " --skin=native --"+flagsname,
                                                       no_stdout=True).spin()
            if status:
                self.ConfigTreeRootInstance.logger.write_error(_("Unable to get Xenomai's %s \n")%flagsname)
            return [result.strip()]
        return []
    
    def getBuilderLDFLAGS(self):
        xeno_ldflags = self.getXenoConfig("ldflags")
        return toolchain_gcc.getBuilderLDFLAGS(self) + xeno_ldflags + ["-shared"]

    def getBuilderCFLAGS(self):
        xeno_cflags = self.getXenoConfig("cflags")
        return toolchain_gcc.getBuilderCFLAGS(self) + xeno_cflags + ["-fPIC"]
        
