name: Build Turnip Zdobersek Branch

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Install Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y ninja-build patchelf unzip flex bison git perl python3-pip glslang-tools
          pip3 install --break-system-packages meson mako

      - name: Setup Environment
        run: |
          mkdir -p turnip_workdir
          chmod +x build_zdobersek.sh

      - name: Build Driver
        run: ./build_zdobersek.sh

      - name: Generate Release Metadata
        id: meta
        run: |
          echo "TAG_NAME=v$(date +'%Y.%m.%d-%H%M')" >> $GITHUB_ENV
          echo "RELEASE_NAME=Turnip Zdobersek Timeline - $(date +'%Y-%m-%d')" >> $GITHUB_ENV

      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: Turnip-Drivers-Pack
          path: turnip_workdir/*.zip
          if-no-files-found: error
          compression-level: 0

      - name: Publish Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ env.TAG_NAME }}
          name: ${{ env.RELEASE_NAME }}
          body: |
            **Turnip Zdobersek Timeline Sync**
            
            * **Repo:** `zdobersek/mesa-fork`
            * **Branch:** `work/tu_kgsl_timeline_sync`
            * **Changes:** Clean build of Zdobersek's timeline sync implementation for KGSL.
          files: turnip_workdir/*.zip
          draft: false
          prerelease: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
