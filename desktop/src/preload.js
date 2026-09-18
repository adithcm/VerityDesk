const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("verityDeskDesktop", {
  runtime: "electron",
});

