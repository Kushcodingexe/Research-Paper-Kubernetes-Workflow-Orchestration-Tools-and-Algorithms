#!/usr/bin/env python3
"""
Montage Workflow Generator for Pegasus
Generates a realistic Montage-style DAG workflow for testing HTCondor pools.

Workflow Stages:
1. mProjectPP  - Reproject input images (parallel)
2. mDiffFit    - Compute differences between overlapping images
3. mConcatFit  - Concatenate fit files
4. mBgModel    - Compute background model
5. mBgExec     - Apply background corrections (parallel)
6. mAdd        - Co-add corrected images
7. mShrink     - Create thumbnail
8. mJPEG       - Convert to JPEG
9. mImgtbl     - Generate image metadata table
"""

import os
import sys
import argparse
import math
from datetime import datetime

from Pegasus.api import (
    Workflow,
    Job,
    File,
    Transformation,
    TransformationCatalog,
    SiteCatalog,
    Site,
    Directory,
    FileServer,
    Operation,
    ReplicaCatalog,
    Properties,
    Namespace,
    Arch,
    OS,
)


class MontageWorkflowGenerator:
    """Generates Montage astronomy workflow for Pegasus."""
    
    def __init__(self, degree=1.0, output_dir='.'):
        """
        Initialize generator.
        
        Args:
            degree: Size of mosaic in degrees (affects number of images)
            output_dir: Output directory for generated files
        """
        self.degree = degree
        self.output_dir = output_dir
        
        # Calculate number of images based on degree
        # Roughly 4 images per 0.5 degrees squared
        self.n_images = max(4, int((degree * 2) ** 2))
        
        # Calculate overlaps (each pair of adjacent images)
        self.n_overlaps = self._calculate_overlaps()
        
        self.wf = None
        self.tc = None
        self.sc = None
        self.rc = None
        
    def _calculate_overlaps(self):
        """Calculate number of image overlaps."""
        # Grid-based overlap calculation
        side = int(math.sqrt(self.n_images))
        # Horizontal + vertical overlaps
        return 2 * side * (side - 1)
    
    def create_transformation_catalog(self):
        """Create transformation catalog with Montage executables."""
        self.tc = TransformationCatalog()
        
        base_path = '/app/executables'
        
        montage_tools = [
            ('mProjectPP', 'Reproject images'),
            ('mDiffFit', 'Difference and fit'),
            ('mConcatFit', 'Concatenate fits'),
            ('mBgModel', 'Background model'),
            ('mBgExec', 'Background execution'),
            ('mAdd', 'Add images'),
            ('mShrink', 'Shrink image'),
            ('mJPEG', 'Create JPEG'),
            ('mImgtbl', 'Image table'),
        ]
        
        for tool_name, desc in montage_tools:
            t = Transformation(
                tool_name,
                namespace='montage',
                version='6.0',
                site='local',
                pfn=f'{base_path}/{tool_name}.py',
                is_stageable=False
            )
            t.add_profiles(Namespace.PEGASUS, key='clusters.size', value='1')
            self.tc.add_transformations(t)
        
        return self.tc
    
    def create_site_catalog(self):
        """Create site catalog for local and condorpool execution."""
        self.sc = SiteCatalog()
        
        # Local site
        local = Site('local', arch=Arch.X86_64, os_type=OS.LINUX)
        local.add_directories(
            Directory(Directory.SHARED_SCRATCH, '/app/scratch')
                .add_file_servers(FileServer('file:///app/scratch', Operation.ALL)),
            Directory(Directory.LOCAL_STORAGE, '/app/output')
                .add_file_servers(FileServer('file:///app/output', Operation.ALL))
        )
        local.add_profiles(Namespace.PEGASUS, key='style', value='condor')
        local.add_profiles(Namespace.CONDOR, key='universe', value='local')
        
        # Condorpool for distributed execution on Vagrant cluster
        condorpool = Site('condorpool', arch=Arch.X86_64, os_type=OS.LINUX)
        condorpool.add_profiles(Namespace.PEGASUS, key='style', value='condor')
        condorpool.add_profiles(Namespace.CONDOR, key='universe', value='vanilla')
        condorpool.add_profiles(Namespace.CONDOR, key='requirements', value='True')
        
        self.sc.add_sites(local, condorpool)
        return self.sc
    
    def create_replica_catalog(self):
        """Create replica catalog for input files."""
        self.rc = ReplicaCatalog()
        
        # Add input images
        for i in range(1, self.n_images + 1):
            self.rc.add_replica('local', File(f'input_{i:03d}.fits'), 
                               f'file:///app/input/input_{i:03d}.fits')
        
        return self.rc
    
    def create_workflow(self):
        """Create the Montage workflow DAG."""
        run_id = f"montage-{self.degree}deg-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.wf = Workflow(run_id)
        
        # ===== STAGE 1: mProjectPP (Parallel Reprojection) =====
        project_jobs = []
        projected_files = []
        
        for i in range(1, self.n_images + 1):
            input_file = File(f'input_{i:03d}.fits')
            output_file = File(f'projected_{i:03d}.fits')
            projected_files.append(output_file)
            
            job = Job('mProjectPP', namespace='montage', version='6.0')
            job.add_args('-X', input_file, output_file)
            job.add_inputs(input_file)
            job.add_outputs(output_file, stage_out=False)
            job.add_profiles(Namespace.PEGASUS, key='label', value=f'project-{i}')
            
            self.wf.add_jobs(job)
            project_jobs.append(job)
        
        # ===== STAGE 2: mImgtbl (Generate Image Table) =====
        imgtbl_out = File('images.tbl')
        imgtbl_job = Job('mImgtbl', namespace='montage', version='6.0')
        imgtbl_job.add_args('-t', str(self.n_images), imgtbl_out)
        for pf in projected_files:
            imgtbl_job.add_inputs(pf)
        imgtbl_job.add_outputs(imgtbl_out, stage_out=False)
        
        self.wf.add_jobs(imgtbl_job)
        for pj in project_jobs:
            self.wf.add_dependency(imgtbl_job, parents=[pj])
        
        # ===== STAGE 3: mDiffFit (Difference Computation) =====
        difffit_jobs = []
        diff_files = []
        fit_files = []
        
        for i in range(1, min(self.n_overlaps + 1, self.n_images)):
            diff_file = File(f'diff_{i:03d}.fits')
            fit_file = File(f'fit_{i:03d}.txt')
            diff_files.append(diff_file)
            fit_files.append(fit_file)
            
            # Each diff uses two adjacent projected images
            img1_idx = i
            img2_idx = (i % self.n_images) + 1
            
            job = Job('mDiffFit', namespace='montage', version='6.0')
            job.add_args(projected_files[img1_idx-1], projected_files[img2_idx-1], 
                        diff_file, fit_file)
            job.add_inputs(projected_files[img1_idx-1], projected_files[img2_idx-1])
            job.add_outputs(diff_file, stage_out=False)
            job.add_outputs(fit_file, stage_out=False)
            
            self.wf.add_jobs(job)
            self.wf.add_dependency(job, parents=[imgtbl_job])
            difffit_jobs.append(job)
        
        # ===== STAGE 4: mConcatFit (Concatenate Fits) =====
        concat_out = File('fits.tbl')
        concat_job = Job('mConcatFit', namespace='montage', version='6.0')
        concat_job.add_args('-o', concat_out)
        for ff in fit_files:
            concat_job.add_inputs(ff)
        concat_job.add_outputs(concat_out, stage_out=False)
        
        self.wf.add_jobs(concat_job)
        for dj in difffit_jobs:
            self.wf.add_dependency(concat_job, parents=[dj])
        
        # ===== STAGE 5: mBgModel (Background Model) =====
        bgmodel_out = File('corrections.tbl')
        bgmodel_job = Job('mBgModel', namespace='montage', version='6.0')
        bgmodel_job.add_args(imgtbl_out, concat_out, bgmodel_out)
        bgmodel_job.add_inputs(imgtbl_out, concat_out)
        bgmodel_job.add_outputs(bgmodel_out, stage_out=False)
        
        self.wf.add_jobs(bgmodel_job)
        self.wf.add_dependency(bgmodel_job, parents=[concat_job])
        
        # ===== STAGE 6: mBgExec (Apply Corrections) =====
        bgexec_jobs = []
        corrected_files = []
        
        for i in range(1, self.n_images + 1):
            corrected_file = File(f'corrected_{i:03d}.fits')
            corrected_files.append(corrected_file)
            
            job = Job('mBgExec', namespace='montage', version='6.0')
            job.add_args(projected_files[i-1], bgmodel_out, corrected_file)
            job.add_inputs(projected_files[i-1], bgmodel_out)
            job.add_outputs(corrected_file, stage_out=False)
            
            self.wf.add_jobs(job)
            self.wf.add_dependency(job, parents=[bgmodel_job])
            bgexec_jobs.append(job)
        
        # ===== STAGE 7: mAdd (Co-add Images) =====
        mosaic_file = File('mosaic.fits')
        add_job = Job('mAdd', namespace='montage', version='6.0')
        add_job.add_args('-o', mosaic_file)
        for cf in corrected_files:
            add_job.add_inputs(cf)
        add_job.add_outputs(mosaic_file, stage_out=True)
        
        self.wf.add_jobs(add_job)
        for bj in bgexec_jobs:
            self.wf.add_dependency(add_job, parents=[bj])
        
        # ===== STAGE 8: mShrink (Create Thumbnail) =====
        thumb_file = File('mosaic_thumb.fits')
        shrink_job = Job('mShrink', namespace='montage', version='6.0')
        shrink_job.add_args(mosaic_file, thumb_file, '0.1')
        shrink_job.add_inputs(mosaic_file)
        shrink_job.add_outputs(thumb_file, stage_out=True)
        
        self.wf.add_jobs(shrink_job)
        self.wf.add_dependency(shrink_job, parents=[add_job])
        
        # ===== STAGE 9: mJPEG (Create JPEG) =====
        jpeg_file = File('mosaic.jpg')
        jpeg_job = Job('mJPEG', namespace='montage', version='6.0')
        jpeg_job.add_args(mosaic_file, jpeg_file)
        jpeg_job.add_inputs(mosaic_file)
        jpeg_job.add_outputs(jpeg_file, stage_out=True)
        
        self.wf.add_jobs(jpeg_job)
        self.wf.add_dependency(jpeg_job, parents=[add_job])
        
        return self.wf
    
    def get_stats(self):
        """Get workflow statistics."""
        n_project = self.n_images
        n_difffit = min(self.n_overlaps, self.n_images - 1)
        n_bgexec = self.n_images
        
        total_jobs = (
            n_project +      # mProjectPP
            1 +              # mImgtbl
            n_difffit +      # mDiffFit
            1 +              # mConcatFit
            1 +              # mBgModel
            n_bgexec +       # mBgExec
            1 +              # mAdd
            1 +              # mShrink
            1                # mJPEG
        )
        
        return {
            'degree': self.degree,
            'n_images': self.n_images,
            'n_overlaps': self.n_overlaps,
            'total_jobs': total_jobs,
            'parallel_stages': 4,  # mProjectPP, mDiffFit, mBgExec, (mShrink||mJPEG)
            'max_parallel': max(n_project, n_difffit, n_bgexec),
        }
    
    def write_all(self):
        """Write workflow and all catalogs."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Workflow
        wf_path = os.path.join(self.output_dir, 'montage.yml')
        self.wf.write(wf_path)
        print(f"Workflow: {wf_path}")
        
        # Transformation Catalog
        tc_path = os.path.join(self.output_dir, 'tc.yml')
        self.tc.write(tc_path)
        print(f"TC: {tc_path}")
        
        # Site Catalog
        sc_path = os.path.join(self.output_dir, 'sites.yml')
        self.sc.write(sc_path)
        print(f"SC: {sc_path}")
        
        # Replica Catalog
        rc_path = os.path.join(self.output_dir, 'rc.yml')
        self.rc.write(rc_path)
        print(f"RC: {rc_path}")
        
        # Properties
        props = Properties()
        props['pegasus.catalog.site.file'] = sc_path
        props['pegasus.catalog.transformation.file'] = tc_path
        props['pegasus.catalog.replica.file'] = rc_path
        props['pegasus.data.configuration'] = 'nonsharedfs'
        props.write(os.path.join(self.output_dir, 'pegasus.properties'))


def main():
    parser = argparse.ArgumentParser(description='Generate Montage Workflow')
    parser.add_argument('--degree', type=float, default=1.0,
                        help='Mosaic size in degrees (default: 1.0)')
    parser.add_argument('--output', default='.',
                        help='Output directory')
    parser.add_argument('--stats', action='store_true',
                        help='Only print statistics')
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"MONTAGE WORKFLOW GENERATOR")
    print(f"{'='*60}")
    print(f"Mosaic Size: {args.degree}°")
    
    gen = MontageWorkflowGenerator(degree=args.degree, output_dir=args.output)
    
    # Generate components
    gen.create_transformation_catalog()
    gen.create_site_catalog()
    gen.create_replica_catalog()
    gen.create_workflow()
    
    # Print stats
    stats = gen.get_stats()
    print(f"\nWorkflow Statistics:")
    print(f"  Input Images: {stats['n_images']}")
    print(f"  Overlaps: {stats['n_overlaps']}")
    print(f"  Total Jobs: {stats['total_jobs']}")
    print(f"  Max Parallel: {stats['max_parallel']}")
    
    if not args.stats:
        print(f"\nGenerating files...")
        gen.write_all()
        print(f"\nDone!")


if __name__ == '__main__':
    main()
