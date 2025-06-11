"""
Configuration Manager for Excluded Folders
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ExcludedFoldersConfig:
    def __init__(self, config_file_path: str = "./config/excluded_folders.json"):
        self.config_file_path = config_file_path
        self.config_data = {}
        self._ensure_config_dir()
        self.load_config()
    
    def _ensure_config_dir(self):
        """設定ディレクトリが存在することを確認"""
        config_dir = os.path.dirname(self.config_file_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            logger.info(f"Created config directory: {config_dir}")
    
    def load_config(self) -> bool:
        """設定ファイルを読み込み"""
        try:
            if not os.path.exists(self.config_file_path):
                logger.info(f"Config file not found: {self.config_file_path}, creating default")
                self._create_default_config()
                return True
            
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
            
            logger.info(f"Loaded excluded folders config with {len(self.get_excluded_folder_ids())} folders")
            return True
            
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            self._create_default_config()
            return False
    
    def _create_default_config(self):
        """デフォルト設定ファイルを作成"""
        default_config = {
            "excluded_folders": [],
            "settings": {
                "auto_exclude_enabled": True,
                "cache_duration_hours": 24,
                "max_excluded_folders": 50
            },
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        self.config_data = default_config
        self.save_config()
    
    def save_config(self) -> bool:
        """設定ファイルを保存"""
        try:
            self.config_data["last_updated"] = datetime.now().isoformat()
            
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved excluded folders config to {self.config_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config file: {e}")
            return False
    
    def get_excluded_folder_ids(self) -> List[str]:
        """有効な除外フォルダIDのリストを取得"""
        try:
            excluded_folders = self.config_data.get("excluded_folders", [])
            return [
                folder["id"] 
                for folder in excluded_folders 
                if folder.get("enabled", True) and folder.get("id")
            ]
        except Exception as e:
            logger.error(f"Error getting excluded folder IDs: {e}")
            return []
    
    def get_excluded_folders(self) -> List[Dict[str, Any]]:
        """除外フォルダの完全な情報を取得"""
        return self.config_data.get("excluded_folders", [])
    
    def add_excluded_folder(self, folder_id: str, name: str = "", description: str = "", enabled: bool = True) -> bool:
        """除外フォルダを追加"""
        try:
            # 既存チェック
            existing_ids = [f["id"] for f in self.config_data.get("excluded_folders", [])]
            if folder_id in existing_ids:
                logger.warning(f"Folder {folder_id} already in excluded list")
                return False
            
            # 最大数チェック
            max_folders = self.config_data.get("settings", {}).get("max_excluded_folders", 50)
            if len(existing_ids) >= max_folders:
                logger.error(f"Maximum excluded folders limit reached: {max_folders}")
                return False
            
            new_folder = {
                "id": folder_id,
                "name": name or f"Folder {folder_id[:8]}",
                "description": description,
                "enabled": enabled,
                "added_date": datetime.now().isoformat()
            }
            
            if "excluded_folders" not in self.config_data:
                self.config_data["excluded_folders"] = []
            
            self.config_data["excluded_folders"].append(new_folder)
            self.save_config()
            
            logger.info(f"Added excluded folder: {folder_id} ({name})")
            return True
            
        except Exception as e:
            logger.error(f"Error adding excluded folder: {e}")
            return False
    
    def remove_excluded_folder(self, folder_id: str) -> bool:
        """除外フォルダを削除"""
        try:
            excluded_folders = self.config_data.get("excluded_folders", [])
            original_count = len(excluded_folders)
            
            self.config_data["excluded_folders"] = [
                f for f in excluded_folders if f.get("id") != folder_id
            ]
            
            if len(self.config_data["excluded_folders"]) < original_count:
                self.save_config()
                logger.info(f"Removed excluded folder: {folder_id}")
                return True
            else:
                logger.warning(f"Folder {folder_id} not found in excluded list")
                return False
                
        except Exception as e:
            logger.error(f"Error removing excluded folder: {e}")
            return False
    
    def toggle_excluded_folder(self, folder_id: str) -> Optional[bool]:
        """除外フォルダの有効/無効を切り替え"""
        try:
            excluded_folders = self.config_data.get("excluded_folders", [])
            
            for folder in excluded_folders:
                if folder.get("id") == folder_id:
                    folder["enabled"] = not folder.get("enabled", True)
                    self.save_config()
                    logger.info(f"Toggled folder {folder_id} to {'enabled' if folder['enabled'] else 'disabled'}")
                    return folder["enabled"]
            
            logger.warning(f"Folder {folder_id} not found in excluded list")
            return None
            
        except Exception as e:
            logger.error(f"Error toggling excluded folder: {e}")
            return None
    
    def is_auto_exclude_enabled(self) -> bool:
        """自動除外が有効かチェック"""
        return self.config_data.get("settings", {}).get("auto_exclude_enabled", True)
    
    def get_settings(self) -> Dict[str, Any]:
        """設定情報を取得"""
        return self.config_data.get("settings", {})
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """設定を更新"""
        try:
            if "settings" not in self.config_data:
                self.config_data["settings"] = {}
            
            self.config_data["settings"].update(settings)
            self.save_config()
            
            logger.info(f"Updated settings: {settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False

# グローバルインスタンス
excluded_folders_config = ExcludedFoldersConfig()