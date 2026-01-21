// Audio Utility - Disabled by user request
class SoundManager {
    constructor() {
        this.enabled = false;
    }

    init() {}
    playTone() {}
    playClick() {}
    playHover() {}
    playAlert() {}
    playWindowOpen() {}
    playSwitch() {}
}

export const soundManager = new SoundManager();