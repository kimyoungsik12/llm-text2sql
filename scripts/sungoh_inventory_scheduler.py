#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성오 재고현황 데이터 스케줄러
매일 실행되어 엑셀 파일에서 월간 데이터를 추출하고 CSV로 저장하는 스케줄러
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging
import sys
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/sungoh_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SungohInventoryScheduler:
    """성오 재고현황 스케줄러 클래스"""
    
    def __init__(self, output_base_dir="../extracted_data"):
        self.base_path = Path("/mnt/sungil/VOL1/ilro/일로 재고관리")
        self.output_base_dir = output_base_dir
        self.month_names = {
            1: "1월", 2: "2월", 3: "3월", 4: "4월", 5: "5월", 6: "6월",
            7: "7월", 8: "8월", 9: "9월", 10: "10월", 11: "11월", 12: "12월"
        }
        self.target_sheets = ["후기 월간", "1동 월간"]
        
        # 카테고리 매핑 (작업 종류)
        self.category_mapping = {
            '입식': 1,
            '전입': 2, 
            '전출': 3,
            '출하': 4,
            '폐사': 5,
            '도태': 6
        }
        
        # 돈사명 매핑 (piggery_id로 사용)
        self.piggery_mapping = {
            '후기 월간': '후기',
            '1동 월간': '1동'
        }
        
        # 출력 디렉토리 생성
        self._ensure_output_directory()
    
    def _ensure_output_directory(self):
        """출력 디렉토리가 존재하는지 확인하고 생성"""
        if not os.path.exists(self.output_base_dir):
            os.makedirs(self.output_base_dir)
            logger.info(f"출력 디렉토리 생성: {self.output_base_dir}")
    
    def get_target_date_info(self, target_date=None):
        """
        대상 날짜의 정보를 반환 (기본값: 어제)
        
        Args:
            target_date (datetime, optional): 대상 날짜. None이면 어제 날짜 사용
            
        Returns:
            tuple: (year, month_name, target_date)
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        year = target_date.year
        month_name = self.month_names[target_date.month]
        
        return year, month_name, target_date
    
    def generate_file_paths(self, target_date=None):
        """
        엑셀 파일의 가능한 경로들을 생성
        
        Args:
            target_date (datetime, optional): 대상 날짜
            
        Returns:
            list: 가능한 파일 경로들의 리스트
        """
        year, month_name, _ = self.get_target_date_info(target_date)
        filename = f"성오 재고현황 {month_name}.xlsx"
        
        # 가능한 경로들
        paths = [
            self.base_path / filename,  # 기본 경로
            self.base_path / str(year) / filename  # 년도 폴더 내 경로
        ]
        
        return paths
    
    def find_excel_file(self, target_date=None):
        """
        엑셀 파일을 찾아서 경로 반환
        
        Args:
            target_date (datetime, optional): 대상 날짜
            
        Returns:
            Path or None: 찾은 파일의 경로, 없으면 None
        """
        year, month_name, date_info = self.get_target_date_info(target_date)
        possible_paths = self.generate_file_paths(target_date)
        
        logger.info(f"날짜: {date_info.strftime('%Y-%m-%d')} ({year}년 {month_name})")
        logger.info("다음 경로들을 확인합니다:")
        
        for path in possible_paths:
            logger.info(f"  - {path}")
            if path.exists():
                logger.info(f"✓ 파일을 찾았습니다: {path}")
                return path
        
        logger.warning("해당 조건에 맞는 엑셀 파일을 찾을 수 없습니다.")
        return None
    
    def read_excel_sheet(self, sheet_name, target_date=None):
        """
        특정 시트의 데이터를 읽어서 pandas DataFrame으로 반환
        
        Args:
            sheet_name (str): 읽을 시트명
            target_date (datetime, optional): 대상 날짜
            
        Returns:
            pandas.DataFrame or None: 읽은 데이터, 실패시 None
        """
        file_path = self.find_excel_file(target_date)
        
        if file_path is None:
            logger.error(f"엑셀 파일을 찾을 수 없어 '{sheet_name}' 시트를 읽을 수 없습니다.")
            return None
        
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            logger.info(f"시트 '{sheet_name}' 읽기 성공: {df.shape[0]}행 × {df.shape[1]}열")
            return df
            
        except Exception as e:
            logger.error(f"시트 '{sheet_name}' 읽기 실패: {e}")
            return None
    
    def filter_previous_day_data(self, df, target_date=None):
        """
        DataFrame에서 전날 데이터만 필터링
        
        Args:
            df (pandas.DataFrame): 전체 월간 데이터
            target_date (datetime, optional): 대상 날짜 (기본: 어제)
            
        Returns:
            pandas.DataFrame or None: 전날 데이터만 포함된 DataFrame
        """
        if df is None or df.empty:
            return None
        
        try:
            # 대상 날짜 정보 가져오기
            _, _, date_info = self.get_target_date_info(target_date)
            target_date_str = date_info.strftime("%Y-%m-%d")
            
            # 헤더 행들 (날짜가 아닌 메타 정보) 보존
            header_rows = []
            data_rows = []
            
            for idx, row in df.iterrows():
                first_col_value = str(row.iloc[0]).strip()
                
                # 날짜 형식인지 확인 (YYYY-MM-DD 또는 YYYY-MM-DD HH:MM:SS)
                if first_col_value.startswith('202') and '-' in first_col_value:
                    # 실제 날짜 데이터 행
                    row_date = first_col_value.split(' ')[0]  # 시간 부분 제거
                    if row_date == target_date_str:
                        data_rows.append(row)
                        logger.info(f"전날 데이터 발견: {row_date}")
                else:
                    # 헤더 행 (날짜, 구분, 컬럼명 등)
                    header_rows.append(row)
            
            if not data_rows:
                logger.warning(f"전날 데이터({target_date_str})를 찾을 수 없습니다.")
                return None
            
            # 헤더 + 전날 데이터만 포함된 새 DataFrame 생성
            filtered_rows = header_rows + data_rows
            filtered_df = pd.DataFrame(filtered_rows).reset_index(drop=True)
            
            logger.info(f"전날 데이터 필터링 완료: {len(data_rows)}행의 실제 데이터")
            return filtered_df
            
        except Exception as e:
            logger.error(f"전날 데이터 필터링 실패: {e}")
            return None
    
    def save_data_to_csv(self, df, sheet_name, target_date=None, daily_only=False):
        """
        DataFrame을 CSV 파일로 저장
        
        Args:
            df (pandas.DataFrame): 저장할 데이터
            sheet_name (str): 시트명 (파일명에 사용)
            target_date (datetime, optional): 대상 날짜
            daily_only (bool): True이면 전날 데이터만 저장
            
        Returns:
            str or None: 저장된 파일 경로, 실패시 None
        """
        if df is None:
            logger.error(f"저장할 데이터가 없습니다: {sheet_name}")
            return None
        
        try:
            # 전날 데이터만 필터링할지 결정
            if daily_only:
                df = self.filter_previous_day_data(df, target_date)
                if df is None:
                    return None
            
            # 파일명에 사용할 날짜 결정 (처리한 데이터의 날짜)
            _, _, date_info = self.get_target_date_info(target_date)
            file_date = date_info.strftime("%Y%m%d")
            
            safe_sheet_name = sheet_name.replace(" ", "_").replace("월간", "monthly")
            
            # 파일명에 daily 구분 추가
            file_suffix = "daily" if daily_only else "monthly"
            csv_filename = f"{self.output_base_dir}/sungoh_{safe_sheet_name}_{file_suffix}_{file_date}.csv"
            
            # CSV 저장
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            logger.info(f"💾 CSV 저장 완료: {csv_filename}")
            
            return csv_filename
            
        except Exception as e:
            logger.error(f"CSV 저장 실패 ({sheet_name}): {e}")
            return None
    
    def parse_csv_to_inventory_changes(self, csv_file_path, sheet_name, target_date=None):
        """
        CSV 파일을 읽어서 재고 변화 JSON 배열로 변환
        
        Args:
            csv_file_path (str): CSV 파일 경로
            sheet_name (str): 시트명 (돈사명 매핑용)
            target_date (datetime, optional): 대상 날짜
            
        Returns:
            list: 재고 변화 기록 JSON 배열
        """
        try:
            df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
            logger.info(f"CSV 파일 읽기 성공: {csv_file_path}")
            
            # 대상 날짜 정보 가져오기
            _, _, date_info = self.get_target_date_info(target_date)
            created_at = date_info.strftime("%Y-%m-%dT09:00:00.000Z")  # 오전 9시 고정
            
            # 돈사명 추출
            piggery_name = self.piggery_mapping.get(sheet_name, sheet_name)
            
            # 날짜 포맷팅 (한국어)
            date_korean = date_info.strftime("%Y년 %m월 %d일")
            
            inventory_changes = []
            
            # 데이터 행 찾기 (날짜로 시작하는 행)
            data_row = None
            room_names = []
            
            for idx, row in df.iterrows():
                first_col = str(row.iloc[0]).strip()
                
                # 실제 데이터 행 찾기
                if first_col.startswith('202') and '-' in first_col:
                    data_row = row
                    break
                
                # 방 이름 정보 추출 (구분 행에서)
                if first_col == '구분':
                    for col_idx, cell in enumerate(row):
                        cell_str = str(cell).strip()
                        if cell_str.endswith('방') and cell_str != '구분':
                            room_names.append(cell_str)
            
            if data_row is None:
                logger.warning("데이터 행을 찾을 수 없습니다.")
                return []
            
            # 헤더 정보에서 작업 종류와 방 정보 매핑
            header_row = None
            for idx, row in df.iterrows():
                if '입식' in str(row.values):
                    header_row = row
                    break
            
            if header_row is None:
                logger.warning("헤더 행을 찾을 수 없습니다.")
                return []
            
            # 각 방별로 작업 데이터 추출
            col_idx = 1  # 첫 번째 컬럼은 날짜이므로 제외
            room_idx = 0
            
            while col_idx < len(data_row) and room_idx < len(room_names):
                room_name = room_names[room_idx]
                
                # 각 방의 8개 작업 항목 (입식, 전입, 전출, 도태, 폐사, 출하, 오류, 재고)
                room_data = {}
                work_types = ['입식', '전입', '전출', '도태', '폐사', '출하', '오류', '재고']
                
                # 해당 방의 모든 데이터 수집
                for i, work_type in enumerate(work_types):
                    if col_idx + i < len(data_row):
                        value = data_row.iloc[col_idx + i]
                        room_data[work_type] = value if pd.notna(value) else 0
                
                # 돈군 생성 여부 판단 (입식 두수와 현재 재고가 같으면 새로운 돈군)
                입식_두수 = room_data.get('입식', 0)
                현재_재고 = room_data.get('재고', 0)
                
                is_herd_created = False
                if (pd.notna(입식_두수) and pd.notna(현재_재고) and 
                    str(입식_두수).replace('.', '').isdigit() and str(현재_재고).replace('.', '').isdigit() and
                    float(입식_두수) > 0 and float(입식_두수) == float(현재_재고)):
                    is_herd_created = True
                    logger.info(f"{piggery_name} {room_name}: 돈군 생성 감지 (입식:{입식_두수}, 재고:{현재_재고})")
                
                # 각 작업 타입별 재고 변화 기록 생성
                for work_type in ['입식', '전입', '전출', '도태', '폐사', '출하']:
                    value = room_data.get(work_type, 0)
                    
                    # 값이 숫자이고 0보다 큰 경우만 처리
                    if pd.notna(value) and str(value).replace('.', '').isdigit() and float(value) > 0:
                        change_count = int(float(value))
                        
                        # 돈군명 생성: "날짜 + 돈방명 + 돈군"
                        herd_name = f"{date_korean} {room_name} 돈군"
                        
                        # JSON 객체 생성
                        change_record = {
                            "category_id": self.category_mapping[work_type],
                            "change": change_count,
                            "created_at": created_at,
                            "piggery_id": piggery_name,
                            "herd_id": herd_name,
                            "is_created": is_herd_created and work_type == '입식'  # 입식이면서 돈군 생성인 경우만 True
                        }
                        
                        # arrival_room_id vs departure_room_id 결정
                        if work_type in ['입식', '전입']:
                            change_record["arrival_room_id"] = room_name
                        else:  # 전출, 출하, 폐사, 도태
                            change_record["departure_room_id"] = room_name
                        
                        inventory_changes.append(change_record)
                        
                        # 돈군 생성 로그 추가
                        created_text = " (돈군 생성)" if change_record["is_created"] else ""
                        logger.info(f"{piggery_name} {room_name} {work_type}: {change_count}두{created_text}")
                
                # 다음 방으로 이동 (8개 컬럼 건너뛰기: 입식,전입,전출,도태,폐사,출하,오류,재고)
                col_idx += 8
                room_idx += 1
            
            logger.info(f"총 {len(inventory_changes)}개의 재고 변화 기록 생성")
            return inventory_changes
            
        except Exception as e:
            logger.error(f"CSV to JSON 변환 실패: {e}")
            return []
    
    def save_unified_inventory_changes_json(self, all_inventory_changes, target_date=None):
        """
        통합 재고 변화 JSON 배열을 하나의 파일로 저장
        
        Args:
            all_inventory_changes (list): 모든 재고 변화 기록 배열
            target_date (datetime, optional): 대상 날짜
            
        Returns:
            str or None: 저장된 파일 경로, 실패시 None
        """
        try:
            # 파일명에 사용할 날짜 결정 (처리한 데이터의 날짜)
            _, _, date_info = self.get_target_date_info(target_date)
            file_date = date_info.strftime("%Y%m%d")
            json_filename = f"{self.output_base_dir}/sungoh_inventory_changes_{file_date}.json"
            
            # JSON 저장 (한글 지원)
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(all_inventory_changes, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 통합 JSON 저장 완료: {json_filename} ({len(all_inventory_changes)}건)")
            return json_filename
            
        except Exception as e:
            logger.error(f"통합 JSON 저장 실패: {e}")
            return None
    
    def extract_and_save_sheet(self, sheet_name, target_date=None, daily_only=False):
        """
        특정 시트를 추출하고 CSV로 저장
        
        Args:
            sheet_name (str): 시트명
            target_date (datetime, optional): 대상 날짜
            daily_only (bool): True이면 전날 데이터만 저장
            
        Returns:
            dict: 처리 결과 정보
        """
        mode_text = "전날 데이터" if daily_only else "월간 데이터"
        logger.info(f"🔍 '{sheet_name}' 시트 처리 시작 ({mode_text})")
        
        # 데이터 읽기
        df = self.read_excel_sheet(sheet_name, target_date)
        
        if df is None:
            return {
                'sheet_name': sheet_name,
                'success': False,
                'error': '데이터 읽기 실패',
                'file_path': None,
                'data_shape': None,
                'daily_only': daily_only
            }
        
        # CSV 저장 (daily_only 옵션 전달)
        csv_path = self.save_data_to_csv(df, sheet_name, target_date, daily_only)
        
        # JSON 변환 (daily_only인 경우에만)
        inventory_changes = []
        
        if csv_path and daily_only:
            inventory_changes = self.parse_csv_to_inventory_changes(csv_path, sheet_name, target_date)
        
        result = {
            'sheet_name': sheet_name,
            'success': csv_path is not None,
            'error': None if csv_path else 'CSV 저장 실패',
            'file_path': csv_path,
            'inventory_changes': inventory_changes,
            'inventory_changes_count': len(inventory_changes),
            'data_shape': df.shape,
            'daily_only': daily_only
        }
        
        if result['success']:
            logger.info(f"✅ '{sheet_name}' 처리 완료: {mode_text}")
        else:
            logger.error(f"❌ '{sheet_name}' 처리 실패")
        
        return result
    
    def run_daily_extraction(self, target_date=None, daily_only=False):
        """
        일일 데이터 추출 실행 (스케줄러 메인 함수)
        
        Args:
            target_date (datetime, optional): 대상 날짜
            daily_only (bool): True이면 전날 데이터만 추출
            
        Returns:
            dict: 전체 처리 결과
        """
        start_time = datetime.now()
        mode_text = "전날 데이터" if daily_only else "월간 데이터"
        
        logger.info("=" * 60)
        logger.info(f"🚀 성오 재고현황 {mode_text} 추출 시작")
        logger.info("=" * 60)
        
        # 날짜 정보 출력
        year, month_name, date_info = self.get_target_date_info(target_date)
        logger.info(f"📅 처리 대상: {date_info.strftime('%Y-%m-%d')} ({year}년 {month_name})")
        logger.info(f"📁 출력 디렉토리: {os.path.abspath(self.output_base_dir)}")
        logger.info(f"🔧 추출 모드: {mode_text}")
        
        results = {
            'start_time': start_time,
            'target_date': date_info,
            'daily_only': daily_only,
            'sheets_processed': [],
            'success_count': 0,
            'total_count': len(self.target_sheets),
            'errors': []
        }
        
        # 각 시트 처리
        all_inventory_changes = []
        
        for sheet_name in self.target_sheets:
            try:
                result = self.extract_and_save_sheet(sheet_name, target_date, daily_only)
                results['sheets_processed'].append(result)
                
                if result['success']:
                    results['success_count'] += 1
                    # 재고 변화 데이터 수집 (통합 JSON용)
                    if daily_only and result.get('inventory_changes'):
                        all_inventory_changes.extend(result['inventory_changes'])
                else:
                    results['errors'].append(f"{sheet_name}: {result['error']}")
                    
            except Exception as e:
                error_msg = f"{sheet_name}: 예외 발생 - {str(e)}"
                results['errors'].append(error_msg)
                logger.error(f"❌ {error_msg}")
        
        # 통합 JSON 저장 (daily_only이고 변화가 있는 경우)
        unified_json_path = None
        if daily_only and all_inventory_changes:
            unified_json_path = self.save_unified_inventory_changes_json(all_inventory_changes, target_date)
        
        results['unified_json_path'] = unified_json_path
        results['total_inventory_changes'] = len(all_inventory_changes)
        
        # 완료 보고
        end_time = datetime.now()
        duration = end_time - start_time
        results['end_time'] = end_time
        results['duration'] = duration
        
        logger.info("-" * 60)
        logger.info(f"📊 {mode_text} 처리 결과 요약:")
        logger.info(f"  • 성공: {results['success_count']}/{results['total_count']} 시트")
        logger.info(f"  • 소요시간: {duration.total_seconds():.2f}초")
        
        if results['errors']:
            logger.warning("⚠️ 오류 발생:")
            for error in results['errors']:
                logger.warning(f"  • {error}")
        
        # 성공한 파일들 목록
        successful_files = [r['file_path'] for r in results['sheets_processed'] if r['success']]
        
        if successful_files:
            logger.info("💾 저장된 CSV 파일들:")
            for file_path in successful_files:
                logger.info(f"  • {file_path}")
        
        # 통합 JSON 파일 정보
        if results.get('unified_json_path'):
            logger.info("📄 통합 JSON 파일:")
            logger.info(f"  • {results['unified_json_path']}")
            logger.info(f"📈 총 재고 변화 기록: {results['total_inventory_changes']}건")
        
        logger.info("=" * 60)
        logger.info(f"🏁 성오 재고현황 {mode_text} 추출 완료")
        logger.info("=" * 60)
        
        return results


def main():
    """스케줄러 메인 함수"""
    import argparse
    
    # 명령줄 인수 파싱
    parser = argparse.ArgumentParser(description='성오 재고현황 데이터 스케줄러')
    parser.add_argument('--daily-only', action='store_true', 
                       help='전날 데이터만 추출 (기본: 전체 월간 데이터)')
    parser.add_argument('--date', type=str, 
                       help='대상 날짜 (YYYY-MM-DD 형식, 기본: 어제)')
    
    args = parser.parse_args()
    
    try:
        # 스케줄러 인스턴스 생성
        scheduler = SungohInventoryScheduler()
        
        # 대상 날짜 파싱
        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d')
                logger.info(f"사용자 지정 날짜: {args.date}")
            except ValueError:
                logger.error(f"잘못된 날짜 형식: {args.date} (YYYY-MM-DD 형식 사용)")
                return 3
        
        # 추출 모드 결정
        daily_only = args.daily_only
        mode_text = "전날 데이터만" if daily_only else "전체 월간 데이터"
        logger.info(f"추출 모드: {mode_text}")
        
        # 일일 추출 실행
        results = scheduler.run_daily_extraction(target_date, daily_only)
        
        # 성공 여부에 따른 종료 코드 결정
        if results['success_count'] == results['total_count']:
            logger.info("✅ 모든 시트 처리 성공")
            return 0
        elif results['success_count'] > 0:
            logger.warning("⚠️ 일부 시트 처리 성공")
            return 1
        else:
            logger.error("❌ 모든 시트 처리 실패")
            return 2
            
    except Exception as e:
        logger.error(f"💥 스케줄러 실행 중 치명적 오류: {e}")
        return 3


if __name__ == "__main__":
    # 스크립트 직접 실행시
    exit_code = main()
    sys.exit(exit_code)
